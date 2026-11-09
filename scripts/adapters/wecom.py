"""企业微信适配器：只能列出会话，读不到群历史消息。

现状（wecom-cli 1.1.0）：
  - `message aibot sessions list` 能拿到机器人最近有往来的会话，
    字段为 chat_id / chat_name / chat_type / last_msg_time。
  - 没有任何接口能读取群的历史消息内容或发送者。

因此这个适配器只能帮你盘点「我在哪些群」，不能统计「我在群里说了多少」。
要完整分档，需要企业管理员开通会话内容存档（需成员授权），
拿到消息后再实现 fetch_messages()。
"""

from adapters.base import Adapter, pick_list, register, run_cli


@register
class WecomAdapter(Adapter):
    name = "wecom"
    can_read_messages = False
    auth_hint = (
        "企业微信需要先授权：wecom-cli auth init --noninteractive，扫码完成后再跑。\n"
        "即使授权成功，wecom-cli 也只能列出会话，无法读取群历史消息，\n"
        "所以这个平台只能盘点群、不能做参与度分档。"
    )

    def list_chats(self):
        payload = run_cli("wecom-cli", ["message", "aibot", "sessions", "list"])
        sessions = pick_list(payload, "sessions")

        chats = []
        for item in sessions:
            chat_id = item.get("chat_id")
            if not chat_id:
                continue
            chats.append({
                "chat_id": chat_id,
                "name": item.get("chat_name") or "(未命名会话)",
                "description": f"type={item.get('chat_type', '')} "
                               f"last={item.get('last_msg_time', '')}",
            })
        return chats
