#!/usr/bin/env python3
"""Step 1: 拉取当前用户加入的群列表。

默认走飞书（lark）：
    python scripts/collect.py --out data/chats_raw.json

企业微信只有会话列表、没有历史消息：
    python scripts/collect.py --source wecom --out data/wecom_chats.json
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import adapters.lark      # noqa: F401  导入即注册
import adapters.wecom     # noqa: F401
from adapters.base import ensure_cli, get_adapter


def main():
    parser = argparse.ArgumentParser(description="拉取群列表")
    parser.add_argument("--source", default="lark", help="平台：lark / wecom")
    parser.add_argument("--out", default="data/chats_raw.json", help="输出文件路径")
    parser.add_argument("--page-size", type=int, default=100, help="每页条数（飞书 1-100）")
    parser.add_argument("--page-limit", type=int, default=100, help="最多翻多少页")
    parser.add_argument("--exclude-muted", action="store_true",
                        help="排除已免打扰的群（飞书）")
    args = parser.parse_args()

    kwargs = {"page_size": args.page_size, "page_limit": args.page_limit,
              "exclude_muted": args.exclude_muted}
    try:
        adapter = get_adapter(args.source)
    except SystemExit:
        raise
    # 适配器构造签名不同，只传它接受的参数
    try:
        adapter = type(adapter)(**kwargs)
    except TypeError:
        pass

    ensure_cli(adapter)
    chats = adapter.list_chats()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "source": adapter.name,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "can_read_messages": adapter.can_read_messages,
                "count": len(chats),
                "chats": chats,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"[{adapter.name}] 拉到 {len(chats)} 个群 → {out}")
    if not adapter.can_read_messages:
        print("注意：该平台读不到群历史消息，只能盘点群，无法做参与度分档。")


if __name__ == "__main__":
    main()
