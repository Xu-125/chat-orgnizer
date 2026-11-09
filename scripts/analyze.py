#!/usr/bin/env python3
"""Step 2: 逐群统计「你在这群的行为」，据此分五档。

只看四件事：你发了多少条、你最后一次说话是什么时候、
最近有没有人 @ 你、这个群本身还活不活。

用法：
    python scripts/analyze.py --input data/chats_raw.json --me "你的显示名" \
        --out data/chats_analyzed.json

知道自己的 open_id 时优先用 --me-id，比按显示名匹配更准。
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------- 判定阈值
# 想改口径就改这里，别去动下面的逻辑。
CONFIG = {
    "window_days": 30,          # 统计消息的时间窗口（天）
    "page_size": 50,            # 每次拉消息条数，CLI 上限 50
    "fetch_pages": 2,           # 每群最多翻几页（2 页 = 约 100 条消息）
    "active_min_msgs": 3,       # 「我在推进」要求的最少发言条数
    "active_within_days": 14,   # 「我在推进」要求最近一次发言在这之内
    "respond_at_within_days": 7,   # 「需我响应」要求最近被 @ 在这之内
    "respond_group_active_days": 14,  # 且群本身在这之内还活跃
    "watching_group_active_days": 30, # 群还活着就至少算「我在关注」
    "watching_my_within_days": 60,    # 群冷但你 60 天内发过言，也算关注
    "idle_group_within_days": 90,     # 90 天内还有动静、你参与过 → 无需处理
    "quiet_group_days": 90,     # 群静默超过这个数 → 可退出
}

TIER_LABEL = {
    "active": "我在推进",
    "respond": "需我响应",
    "watching": "我在关注",
    "idle": "无需处理",
    "quit": "可退出",
}


def run_cli(args, retries=1):
    """调用 lark-cli 并解析 JSON。消息接口偶发返回非 JSON，重试一次。"""
    last_err = None
    for _ in range(retries + 1):
        try:
            proc = subprocess.run(
                ["lark-cli"] + args, capture_output=True, text=True, timeout=300
            )
            if proc.returncode != 0:
                last_err = (proc.stderr or proc.stdout)[:200]
                time.sleep(1)
                continue
            return json.loads(proc.stdout)
        except (json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
            last_err = str(exc)[:200]
            time.sleep(1)
    raise RuntimeError(f"lark-cli 调用失败：{last_err}")


def parse_time(value):
    """兼容毫秒时间戳字符串与常见日期格式的宽松解析。"""
    if value is None or value == "":
        return None
    text = str(value).strip()
    if text.isdigit():
        num = int(text)
        if num > 10**12:      # 毫秒
            num //= 1000
        return datetime.fromtimestamp(num)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def text_of(message):
    """把消息正文拉成纯文本，用于兜底判断，不参与分档。"""
    content = message.get("content")
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    return str(content or "")


def is_me(sender, me_name, me_id):
    if not sender:
        return False
    if me_id and sender.get("id") == me_id:
        return True
    if me_name and sender.get("name") == me_name:
        return True
    return False


def fetch_messages(chat_id):
    args = [
        "im", "+chat-messages-list",
        "--chat-id", chat_id,
        "--page-size", str(CONFIG["page_size"]),
        "--page-all",
        "--page-limit", str(CONFIG["fetch_pages"]),
        "--order", "desc",
        "--no-reactions",
        "--format", "json",
    ]
    payload = run_cli(args)
    data = payload.get("data", payload)
    for key in ("messages", "data", "items"):
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, list):
            return value
    return []


def classify(stats):
    """按优先级判定档位，返回 (tier, basis)。"""
    my_age = stats["my_age_days"]
    grp_age = stats["group_age_days"]
    my_msgs = stats["my_msgs"]
    at_recent = stats["at_me_recent"]

    if my_msgs >= CONFIG["active_min_msgs"] and my_age is not None \
            and my_age <= CONFIG["active_within_days"]:
        return "active", f"{stats['group_msgs']} 条消息里你发了 {my_msgs} 条，最近 {my_age} 天前还在说话"

    if at_recent >= 1 and grp_age is not None \
            and grp_age <= CONFIG["respond_group_active_days"]:
        return "respond", f"最近 {CONFIG['respond_at_within_days']} 天被 @ {at_recent} 次，群 {grp_age} 天前还有消息"

    if grp_age is not None and grp_age <= CONFIG["watching_group_active_days"]:
        return "watching", f"群 {grp_age} 天前仍有消息，你这段没发言"

    if my_age is not None and my_age <= CONFIG["watching_my_within_days"]:
        return "watching", f"群已冷，但你 {my_age} 天前发过言"

    if my_msgs > 0 and grp_age is not None \
            and grp_age <= CONFIG["idle_group_within_days"]:
        return "idle", f"群 {grp_age} 天没动静，你最后一次发言在 {my_age} 天前"

    if stats["group_msgs"] == 0:
        return "quit", "没有任何可读消息"

    if grp_age is None or grp_age > CONFIG["quiet_group_days"]:
        return "quit", f"群静默 {grp_age} 天" if grp_age else "群已静默"

    return "quit", "你从没在这群发过言，群也基本不动"


def analyze_one(chat, me_name, me_id, now):
    chat_id = chat["chat_id"]
    try:
        messages = fetch_messages(chat_id)
    except RuntimeError as exc:
        return {
            "chat_id": chat_id,
            "name": chat.get("name"),
            "tier": "unknown",
            "basis": f"读取失败：{exc}",
            "my_msgs": None,
            "my_last": None,
            "at_me": None,
            "group_last": None,
            "group_msgs": None,
        }

    window_start = now - timedelta(days=CONFIG["window_days"])
    at_cut = now - timedelta(days=CONFIG["respond_at_within_days"])

    my_msgs = 0
    my_last = None
    at_me = 0
    at_me_recent = 0
    group_last = None
    counted = 0

    for msg in messages:
        if msg.get("deleted"):
            continue
        ts = parse_time(msg.get("create_time"))
        counted += 1
        if ts and (group_last is None or ts > group_last):
            group_last = ts

        sender = msg.get("sender") or {}
        if is_me(sender, me_name, me_id):
            my_msgs += 1
            if my_last is None or (ts and ts > my_last):
                my_last = ts

        for mention in msg.get("mentions") or []:
            if is_me(mention, me_name, me_id):
                at_me += 1
                if ts and ts >= at_cut:
                    at_me_recent += 1
                break

    my_age = (now - my_last).days if my_last else None
    grp_age = (now - group_last).days if group_last else None

    stats = {
        "my_msgs": my_msgs,
        "my_last": my_last.strftime("%Y-%m-%d") if my_last else None,
        "group_msgs": counted,
        "group_last": group_last.strftime("%Y-%m-%d") if group_last else None,
        "my_age_days": my_age,
        "group_age_days": grp_age,
        "at_me": at_me,
        "at_me_recent": at_me_recent,
    }
    tier, basis = classify(stats)

    return {
        "chat_id": chat_id,
        "name": chat.get("name"),
        "description": chat.get("description", ""),
        "tier": tier,
        "tier_label": TIER_LABEL.get(tier, tier),
        "my_msgs": my_msgs,
        "my_last": stats["my_last"],
        "at_me": at_me,
        "at_me_7d": at_me_recent,
        "group_msgs": counted,
        "group_last": stats["group_last"],
        "basis": basis,
        "window_days": CONFIG["window_days"],
    }


def main():
    parser = argparse.ArgumentParser(description="逐群统计参与度并分档")
    parser.add_argument("--input", default="data/chats_raw.json", help="collect.py 的输出")
    parser.add_argument("--out", default="data/chats_analyzed.json", help="输出文件路径")
    parser.add_argument("--me", help="你在飞书里的显示名")
    parser.add_argument("--me-id", help="你的 open_id（ou_xxx），比显示名更准")
    parser.add_argument("--limit", type=int, help="只分析前 N 个群，用来先试跑")
    parser.add_argument("--sleep", type=float, default=0.2, help="每次请求之间的间隔秒数")
    args = parser.parse_args()

    if not args.me and not args.me_id:
        sys.exit("必须给 --me（显示名）或 --me-id（open_id）其中之一，否则认不出哪条是你发的。")

    src = Path(args.input)
    if not src.exists():
        sys.exit(f"找不到 {src}，先跑 collect.py。")
    payload = json.loads(src.read_text(encoding="utf-8"))
    chats = payload.get("chats", payload if isinstance(payload, list) else [])
    if args.limit:
        chats = chats[: args.limit]

    now = datetime.now()
    results = []
    for index, chat in enumerate(chats, 1):
        print(f"[{index}/{len(chats)}] {chat.get('name')}", flush=True)
        results.append(analyze_one(chat, args.me, args.me_id, now))
        time.sleep(args.sleep)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "config": CONFIG,
                "count": len(results),
                "chats": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    tally = {}
    for row in results:
        tally[row["tier"]] = tally.get(row["tier"], 0) + 1
    summary = "，".join(
        f"{TIER_LABEL.get(k, k)} {v}" for k, v in sorted(tally.items())
    )
    print(f"\n完成 {len(results)} 个群：{summary}\n→ {out}")


if __name__ == "__main__":
    main()
