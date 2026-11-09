# 平台支持情况

这套东西能不能用，取决于平台给不给两样数据：**群列表**和**群历史消息（含发送者与 @）**。后者是关键——只拿到群列表，最多能盘点"我在多少个群"，算不出"我在这个群投入多少"。

## 现状

| 平台 | 群列表 | 历史消息 | 能否完整分档 | 说明 |
|---|---|---|---|---|
| 飞书 | ✅ | ✅ | ✅ | 走 `lark-cli`，用户态 token 直接读 |
| 企业微信 | ⚠️ | ❌ | ❌ | `wecom-cli` 只有 `message aibot sessions list`，能列会话名称和最后消息时间，没有读消息内容的接口 |
| 钉钉 | ❌ | ❌ | ❌ | 本机没有钉钉命令行；要接需企业内部应用 + 群会话读取权限，得走开放平台申请 |
| 个人微信 | ❌ | ❌ | ❌ | 无官方 API，只能靠第三方协议或模拟点击，违反用户协议且有封号风险，不做 |

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

钉钉走开放平台企业内部应用，需要 `chat` 相关权限（群列表、群消息读取）。目前没有现成 CLI，得自己调 HTTP 接口。接法是同一套：新建 `adapters/dingtalk.py`，实现 `list_chats()` 和 `fetch_messages()`，返回上面那个统一结构。

## 加一个新平台

1. 在 `scripts/adapters/` 下新建 `xxx.py`
2. 写一个类，继承 `Adapter`，用 `@register` 装饰，设 `name` / `can_read_messages` / `auth_hint`
3. 实现 `list_chats()`；支持读消息的话再实现 `fetch_messages()`
4. 在 `collect.py` / `analyze.py` 顶部的 import 里加一行

如果平台只能列群不能读消息，`can_read_messages = False`，`analyze.py` 会主动拦住并说明原因，不会产出一份全是「可退出」的假结果。
