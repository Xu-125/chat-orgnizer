#!/usr/bin/env python3
"""Step 2.5: 按项目给群打标签。

参与度五档回答"我在这群投入多少"；
项目标签回答"这个群在为哪个项目干活"。两者正交，可以叠在同一个群上。

项目配置写在一个 JSON 文件里，每个项目给一个名字、一组关键词、
和一份白名单 chat_id（兜住"群名根本看不出是哪个项目"的代号群）：

    {
      "projects": [
        {
          "name": "易中天项目",
          "keywords": ["易中天", "易老师", "厦大", "厦门", "12.4", "12/4", "双人记录"],
          "chats": ["oc_xxxxxxxx"]
        },
        {
          "name": "洪晃项目",
          "keywords": ["洪晃", "晃姐", "下苑村", "1125", "昌平", "SKOL", "罗叔"],
          "chats": []
        }
      ]
    }

用法：
    python scripts/projects.py \
        --input data/chats_raw.json \
        --projects examples/projects.example.json \
        --out data/chats_with_projects.json
"""

import argparse
import json
from pathlib import Path


def chat_text(chat):
    return (chat.get("name", "") + " " + chat.get("description", "")).lower()


def match_project(chat, project):
    text = chat_text(chat)
    if chat.get("chat_id") in project.get("chats", []):
        return True
    for kw in project.get("keywords", []):
        if kw.lower() and kw.lower() in text:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description="按项目给群打标签")
    parser.add_argument("--input", default="data/chats_raw.json")
    parser.add_argument("--projects", required=True, help="项目配置 JSON")
    parser.add_argument("--out", default="data/chats_with_projects.json")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    chats = payload.get("chats", payload if isinstance(payload, list) else [])
    cfg = json.loads(Path(args.projects).read_text(encoding="utf-8"))
    projects = cfg.get("projects", [])

    tagged = {p["name"]: [] for p in projects}
    for chat in chats:
        hits = [p["name"] for p in projects if match_project(chat, p)]
        chat["projects"] = hits
        for name in hits:
            tagged[name].append(chat.get("name"))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"count": len(chats), "chats": chats},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"共 {len(chats)} 个群，项目命中分布：")
    for name, names in tagged.items():
        print(f"  {name}: {len(names)} 个群")
        for n in names:
            print(f"    - {n}")
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
