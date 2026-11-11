# 平台支持情况

这套东西能不能用，取决于平台给不给两样数据：**群列表**和**群历史消息（含发送者与 @）**。后者是关键——只拿到群列表，最多能盘点"我在多少个群"，算不出"我在这个群投入多少"。

看支持情况要分两层：**接口层**是平台开放了什么能力，跟用谁的机器无关；**本机层**是命令行工具装没装、登没登，这是运行时探测的环境状态——换台机器装好、授权好就能用，不写死在结论里。

## 现状

| 平台 | 接口层：群列表 | 接口层：历史消息 | 能否完整分档 | 说明 |
|---|---|---|---|---|
| 飞书 | ✅ | ✅ | ✅ | 走 `lark-cli`，用户态 token 直接读 |
| 企业微信 | ⚠️ | ❌ | ❌ | `wecom-cli` 只有 `message aibot sessions list`，能列会话名称和最后消息时间，没有读消息内容的接口 |
| 钉钉 | 仓库内未接 | 仓库内未接 | — | 需先有企业内部应用和群会话读取权限，再补适配器；不取决于本机是否装了钉钉客户端 |
| 个人微信 | ❌ | ❌ | ❌ | 无官方 API，只能靠第三方协议或模拟点击，违反用户协议且有封号风险，不做 |

## 本机环境探测

脚本启动时用 `ensure_cli()` 检查对应 CLI 是否在本机 PATH 里：找不到命令就退出并给出安装指引，不会把"没装 CLI"误判成"平台不支持"。已登录/授权状态再通过一次轻量接口调用确认。

## 企业微信为什么只能做一半

`wecom-cli` 的 message 域给的是"机器人最近有往来的会话"，字段只有 `chat_id` / `chat_name` / `chat_type` / `last_msg_time`。它面向的是"给这个群发消息"，不是"读这个群里发生过什么"。

要拿到消息内容，企业侧需要开通**会话内容存档**：管理员在后台开启、成员逐一授权，且只覆盖开通之后的消息。这是一条合规路径，但门槛在企业管理员手里，不是个人能自己打开的。

拿到存档数据后，只要实现 `adapters/wecom.py` 里的 `fetch_messages()`，把每条消息映射成：

```python
{
    "create_time": "2026-11-01 10:22:33",
    "sender": {"id": "...", "name": "..."},
    "mentions": [{"id": "...", "name": "..."}],
    "deleted": False,
}
```

`analyze.py` 和 `report.py` 不用改一个字。

## 钉钉怎么接

钉钉走开放平台企业内部应用，需要 `chat` 相关权限（群列表、群消息读取）。本仓库未提供钉钉适配器，接法是同一套：新建 `adapters/dingtalk.py`，实现 `list_chats()` 和 `fetch_messages()`，返回上面那个统一结构。

## 加一个新平台

1. 在 `scripts/adapters/` 下新建 `xxx.py`
2. 写一个类，继承 `Adapter`，用 `@register` 装饰，设 `name` / `can_read_messages` / `auth_hint`
3. 实现 `list_chats()`；支持读消息的话再实现 `fetch_messages()`
4. 在 `collect.py` / `analyze.py` 顶部的 import 里加一行

如果平台只能列群不能读消息，`can_read_messages = False`，`analyze.py` 会主动拦住并说明原因，不会产出一份全是「可退出」的假结果。

---

## English notes

### Required data and current support

Full classification needs both a **group list** and **message history with sender and mention information**. A list alone tells you how many groups exist, not how much you participate.

- **Lark / Feishu:** the adapter uses authenticated user access through `lark-cli` for group lists and message history.
- **WeCom:** the current CLI exposes `message aibot sessions list`, with `chat_id`, `chat_name`, `chat_type`, and `last_msg_time`. It lists sessions recently used by the bot, not their full message history. Full classification is unavailable.
- **DingTalk:** no ready-to-use CLI adapter is included. Integration requires an enterprise application and authorized group-list/message access through the platform's supported interfaces.
- **Personal WeChat:** unsupported. The project does not use unofficial protocols or simulated clicks.

CLI availability and sign-in status are detected at runtime, not recorded as a fixed platform verdict: if the command is missing locally, the script exits with an install hint instead of assuming the platform is unsupported.

### Extending WeCom

Authorized enterprise conversation archiving is a possible source of messages. It requires administrator setup and member authorization and covers messages after activation; it is not a switch an individual user can enable alone.

If authorized archive data is available, implement `fetch_messages()` in `scripts/adapters/wecom.py` and map each message to the normalized Python structure shown above: `create_time`, `sender`, `mentions`, and `deleted`. The analyzer and report generator can then use that structure without changes.

### Adding another platform

1. Add `xxx.py` under `scripts/adapters/`.
2. Implement a class inheriting from `Adapter`, decorate it with `@register`, and set `name`, `can_read_messages`, and `auth_hint`.
3. Implement `list_chats()` and, where authorized message reading is supported, `fetch_messages()`.
4. Import the adapter in `collect.py` and `analyze.py`.

For DingTalk, this means adding `scripts/adapters/dingtalk.py` with the same normalized return structure and appropriate platform authorization.

If a platform can list groups but not read messages, keep `can_read_messages = False`. `analyze.py` will stop with an explanation rather than generate a misleading “Can leave” classification for every group.
