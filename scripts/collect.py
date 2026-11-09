#!/usr/bin/env python3
"""Step 1: 拉取当前用户加入的群列表。

依赖：本机已安装并登录 lark-cli（用户身份）。

用法：
    python scripts/collect.py --out data/chats_raw.json
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_cli(args):
    """调用 lark-cli，返回解析后的 JSON；失败时退出并打印 stderr。"""
    try:
        proc = subprocess.run(
            ["lark-cli"] + args, capture_output=True, text=True, timeout=600
        )
    except FileNotFoundError:
        sys.exit("找不到 lark-cli，请先安装并在 PATH 里。")
    if proc.returncode != 0:
        sys.exit("lark-cli 调用失败：\n" + (proc.stderr or proc.stdout)[:800])
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        sys.exit("lark-cli 返回的不是 JSON，请确认命令带了 --format json。")


def pick_list(payload, key):
    """从返回体里取数组。不同版本 CLI 的层级略有差异，这里做兼容。"""
    data = payload.get("data", payload)
    candidates = [data.get(key), data.get("data"), data.get("items"), data.get("chats")]
    for item in candidates:
        if isinstance(item, list):
            return item
    sys.exit("解析返回体失败，没找到列表字段。返回片段：\n" + json.dumps(payload)[:400])


def main():
    parser = argparse.ArgumentParser(description="拉取飞书群列表")
    parser.add_argument("--out", default="data/chats_raw.json", help="输出文件路径")
    parser.add_argument("--page-size", type=int, default=100, help="每页条数，1-100")
    parser.add_argument("--page-limit", type=int, default=100,
                        help="最多翻多少页（默认 100 页，够覆盖上千个群）")
    parser.add_argument("--exclude-muted", action="store_true",
                        help="排除已免打扰的群（如果这些群本来就不需要关心）")
    args = parser.parse_args()

    cmd = [
        "im", "+chat-list",
        "--as", "user",
        "--page-all",
        "--page-size", str(args.page_size),
        "--page-limit", str(args.page_limit),
        "--format", "json",
    ]
    if args.exclude_muted:
        cmd.append("--exclude-muted")

    payload = run_cli(cmd)
    raw = pick_list(payload, "chats")

    chats = []
    for c in raw:
        chats.append({
            "chat_id": c.get("chat_id"),
            "name": c.get("name") or "(未命名群)",
            "description": c.get("description") or "",
            "chat_mode": c.get("chat_mode") or "group",
            "chat_status": c.get("chat_status") or "normal",
        })

    chats = [c for c in chats if c["chat_id"] and c["chat_status"] == "normal"]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "count": len(chats),
                "chats": chats,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"拉到 {len(chats)} 个群 → {out}")


if __name__ == "__main__":
    main()
