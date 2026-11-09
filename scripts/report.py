#!/usr/bin/env python3
"""Step 3: 把分析结果排成一份可以直接看的清单。

用法：
    python scripts/report.py --input data/chats_analyzed.json --out report.md
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

TIER_ORDER = ["active", "respond", "watching", "idle", "quit", "unknown"]

TIER_INFO = {
    "active": ("我在推进", "每天看一眼，有事当天回"),
    "respond": ("需我响应", "尽快回，别让对方等"),
    "watching": ("我在关注", "有空扫一眼，不用回"),
    "idle": ("无需处理", "不用管，留着当入口"),
    "quit": ("可退出", "确认后可以退"),
    "unknown": ("读取失败", "需要手动确认"),
}


def main():
    parser = argparse.ArgumentParser(description="生成群聊分组清单")
    parser.add_argument("--input", default="data/chats_analyzed.json")
    parser.add_argument("--out", default="report.md")
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        raise SystemExit(f"找不到 {src}，先跑 analyze.py。")
    payload = json.loads(src.read_text(encoding="utf-8"))
    rows = payload.get("chats", payload if isinstance(payload, list) else [])
    total = len(rows)

    buckets = {tier: [] for tier in TIER_ORDER}
    for row in rows:
        buckets.setdefault(row.get("tier", "unknown"), []).append(row)

    lines = [
        "# 群聊分组清单",
        "",
        f"共 {total} 个群，生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}。",
        "",
        "## 总览",
        "",
        "| 档位 | 群数 | 占比 | 你要做什么 |",
        "|---|---|---|---|",
    ]
    for tier in TIER_ORDER:
        items = buckets.get(tier) or []
        if not items:
            continue
        label, action = TIER_INFO[tier]
        share = len(items) / total * 100 if total else 0
        lines.append(f"| {label} | {len(items)} | {share:.0f}% | {action} |")

    lines.append("")

    for tier in TIER_ORDER:
        items = buckets.get(tier) or []
        if not items:
            continue
        label, action = TIER_INFO[tier]
        lines.append(f"## {label}（{len(items)} 个）")
        lines.append("")
        lines.append(f"→ {action}")
        lines.append("")
        for item in sorted(items, key=lambda r: r.get("group_last") or "", reverse=True):
            last = item.get("group_last") or "无记录"
            basis = item.get("basis") or ""
            lines.append(f"- **{item.get('name')}** — {basis}（群最后活跃 {last}）")
        lines.append("")

    lines += [
        "## 下一步",
        "",
        "1. 把「我在推进」「需我响应」两档的群放进飞书侧边栏的置顶分组，日常只看这两组。",
        "2. 「可退出」那一档整理成一张退货清单，逐条确认后手动退群——飞书没有批量退群接口。",
        "3. 归档同理：飞书群的归档是客户端操作，接口未开放。这套流程只负责识别和标记，最后一步要自己点。",
        "4. 一个月后再跑一次。群活跃度会漂移，一次分类顶不了一年。",
        "",
    ]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"已生成 {out}（{total} 个群）")


if __name__ == "__main__":
    main()
