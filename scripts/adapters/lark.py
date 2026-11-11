"""飞书适配器：走 lark-cli，以用户身份读群列表和群消息。"""

from adapters.base import Adapter, pick_list, register, run_cli


@register
class LarkAdapter(Adapter):
    name = "lark"
    can_read_messages = True
    cli = "lark-cli"
    install_hint = "安装飞书官方 lark-cli 命令行，并把它放到 PATH。"
    auth_hint = "先运行 lark-cli im +chat-list --as user --page-size 1 --format json 确认用户态登录有效。"

    def __init__(self, page_size=100, page_limit=100, exclude_muted=False,
                 msg_page_size=50, msg_pages=2):
        self.page_size = min(page_size, 100)
        self.page_limit = page_limit
        self.exclude_muted = exclude_muted
        self.msg_page_size = min(msg_page_size, 50)   # 消息接口上限 50
        self.msg_pages = msg_pages

    def list_chats(self):
        args = [
            "im", "+chat-list",
            "--as", "user",
            "--page-all",
            "--page-size", str(self.page_size),
            "--page-limit", str(self.page_limit),
            "--format", "json",
        ]
        if self.exclude_muted:
            args.append("--exclude-muted")

        payload = run_cli("lark-cli", args, timeout=600)
        raw = pick_list(payload, "chats")

        chats = []
        for item in raw:
            if item.get("chat_status") not in (None, "normal"):
                continue
            if not item.get("chat_id"):
                continue
            chats.append({
                "chat_id": item["chat_id"],
                "name": item.get("name") or "(未命名群)",
                "description": item.get("description") or "",
            })
        return chats

    def fetch_messages(self, chat_id):
        args = [
            "im", "+chat-messages-list",
            "--chat-id", chat_id,
            "--page-size", str(self.msg_page_size),
            "--page-all",
            "--page-limit", str(self.msg_pages),
            "--order", "desc",
            "--no-reactions",
            "--format", "json",
        ]
        payload = run_cli("lark-cli", args)
        return pick_list(payload, "messages")
