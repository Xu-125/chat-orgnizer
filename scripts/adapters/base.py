"""适配器基类与公共工具。

统一数据结构：

    群（chat）
        {"chat_id": str, "name": str, "description": str}

    消息（message）
        {"create_time": 原始时间, "sender": {"id": str, "name": str},
         "mentions": [{"id": str, "name": str}], "deleted": bool}

各平台只要把字段映射成上面的形状，analyze.py 和 report.py 就可以直接复用。
"""

import json
import subprocess
import sys
import time


class Adapter:
    """平台适配器协议。"""

    name = "base"
    #: 该平台是否能读到群历史消息。为 False 时只能列群，不能统计参与度。
    can_read_messages = False
    #: 该平台是否需要额外授权，写进报错信息给用户看。
    auth_hint = ""

    def list_chats(self):
        raise NotImplementedError

    def fetch_messages(self, chat_id):
        raise NotImplementedError(
            f"{self.name} 适配器不支持读取群历史消息，无法统计参与度。"
            + (f"\n{self.auth_hint}" if self.auth_hint else "")
        )


def pick_list(payload, *keys):
    """从 CLI 返回体里取数组。不同版本层级略有差异，这里做兼容。"""
    if isinstance(payload, list):
        return payload
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    for key in keys + ("data", "items"):
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, list):
            return value
    return []


def run_cli(cmd, args, retries=1, timeout=300):
    """调用平台 CLI 并解析 JSON。消息接口偶发返回非 JSON，重试一次。"""
    last_err = None
    for _ in range(retries + 1):
        try:
            proc = subprocess.run(
                [cmd] + args, capture_output=True, text=True, timeout=timeout
            )
            if proc.returncode != 0:
                last_err = (proc.stderr or proc.stdout)[:300]
                time.sleep(1)
                continue
            return json.loads(proc.stdout)
        except FileNotFoundError:
            sys.exit(f"找不到 {cmd}，请先安装并在 PATH 里。")
        except (json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
            last_err = str(exc)[:300]
            time.sleep(1)
    raise RuntimeError(f"{cmd} 调用失败：{last_err}")


REGISTRY = {}


def register(adapter_cls):
    REGISTRY[adapter_cls.name] = adapter_cls
    return adapter_cls


def get_adapter(source):
    if source not in REGISTRY:
        raise SystemExit(
            f"未知平台：{source}。可用：{', '.join(sorted(REGISTRY))}"
        )
    return REGISTRY[source]()
