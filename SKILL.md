---
name: chat-orgnizer
description: 用飞书 CLI 按「用户自己的参与度」给群聊分五档（我在推进/需我响应/我在关注/无需处理/可退出），产出一份分组清单。当用户说群太多看不清、被拉进群不知道要干嘛、想把不用的群归置起来、想给群聊分类或盘点自己加入的群时使用。 Use this skill to inventory and organize Lark group chats into five participation-based tiers when the user has too many groups, is unsure what needs attention, or wants to review unused groups.
---

# chat-orgnizer

把用户被动加入的一堆飞书群，按**用户自身的行为数据**分档，而不是按群的名字或性质分。

## 什么时候用

- "我被拉进好多群，不知道每个群要我干嘛"
- "群太多了，能不能帮我理一下哪些该退"
- "项目结束的群就荒废了，想归置起来"
- 需要盘点一次"我到底在多少个群里、哪些还在占用我"

不适用：只是想看某个群最近聊了什么（那是读消息，不是分档）。

## 前置检查

```bash
lark-cli im +chat-list --as user --page-size 1 --format json
```

返回带 `chat_id` 就说明登录态和权限都正常。失败时先解决登录，不要继续往下跑。

## 三步工作流

```bash
python scripts/collect.py --out data/chats_raw.json
python scripts/analyze.py --input data/chats_raw.json --me "<用户显示名>" --out data/chats_analyzed.json
python scripts/report.py --input data/chats_analyzed.json --out report.md
```

1. **collect.py** 拉群列表。想先试跑加 `--page-limit 1`。
2. **analyze.py** 逐群统计并分档。必须传 `--me`（用户飞书显示名）或 `--me-id`（open_id，更准）。群多时串行耗时，`--limit 10` 可以只跑前十个确认口径。
3. **report.py** 出 Markdown 清单。

跑完把 `report.md` 交给用户，重点给「我在推进」「需我响应」两档；「可退出」单独列成候选清单，强调要用户自己确认后退群。

## 项目维度（除了参与度五档）

如果用户问"按项目把群分一下"（例如正在推进的书、直播、纪录片），用 `scripts/projects.py`：

- 准备一份项目配置（参考 `examples/projects.example.json`），每个项目给 `name`、`keywords`、`chats`（白名单）
- `chats` 白名单专门兜住"群名根本看不出是哪个项目"的代号群（比如"小三"、"鲨丁鱼"）——不要指望关键词能命中它们
- 输出在每个群上加 `projects: ["易中天项目", ...]`，可以和参与度档位叠加

## 平台支持

| 平台 | 完整分档 | 说明 |
|---|---|---|
| 飞书 | ✅ | `--source lark`，默认 |
| 企业微信 | ❌ | `--source wecom` 只能列会话，读不到消息，分析会被拦住 |
| 钉钉 / 个人微信 | ❌ | 无 CLI / 无官方 API |

用户问"能不能用在微信、钉钉"时，如实说明瓶颈是**读不到群历史消息**，不是脚本写不写得出来。详见 [docs/adapters.md](docs/adapters.md)。

## 判定口径（脚本已实现，改口径改 CONFIG）

| 档位 | 条件 |
|---|---|
| 我在推进 | 发言 ≥3 条且最近 14 天内有发言 |
| 需我响应 | 最近 7 天被 @ ≥1 次且群 14 天内还有消息 |
| 我在关注 | 群 30 天内还有消息；或群已冷但用户 60 天内发过言 |
| 无需处理 | 用户参与过，群 90 天内还有零星消息 |
| 可退出 | 群静默 >90 天 / 用户从未发言且群不动 / 无可读消息 |

按顺序取第一个命中项。完整口径和误判类型见 [docs/method.md](docs/method.md)。

## 交付时要说清的三件事

1. **飞书群归档是客户端操作，OpenAPI 未开放。** 不能承诺"自动归档"，只能做到识别、标记、分组、提醒。
2. **没有批量退群接口。** 「可退出」只能给清单。
3. **分档是行为推断，不是业务判断。** 群名像核心群但用户从不发言的，会被判「我在关注」；反过来也可能有群名不起眼但真在推进的。让用户扫一眼结果再定。

## 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| `chat-messages-list` 返回非 JSON | 接口偶发异常 | 脚本已内置重试一次；连续失败则该群标 `unknown` |
| 认不出用户自己的消息 | 显示名改过 / 重名 | 改用 `--me-id ou_xxx` |
| `--page-size` 报错 | 消息接口上限 50 | 不要超过 50 |
| 群数量多时耗时 | 每群一次请求 | 可加 `--sleep 0` 提速，但注意限流 |
| 拉不到某群消息 | 新群 / 纯通知群 | 会判「可退出」并标注无消息记录，需人工复核 |

## 隐私

不要把真实的 `data/` 或 `report.md` 提交到公开仓库。`.gitignore` 已排除 `data/` 和 `report.md`。

---

## English instructions

The English notes describe the same workflow; they do not change the scripts, thresholds, or authorization requirements.

### Purpose and triggers

Classify Lark groups by the user's own behavior rather than group names or types. Use this when the user has too many groups, does not know what is expected of them, wants to review finished project groups, or needs an inventory of which groups still require attention. Do not use it merely to summarize recent messages in one group.

### Prerequisite and workflow

Run the access check shown above. A response containing `chat_id` confirms access. If it fails, resolve authentication before continuing.

Use the three commands in the Chinese workflow. Supply the actual display name with `--me`, or use `--me-id` for more reliable matching. Use `--page-limit 1` for a small collection trial and `--limit 10` for a small analysis trial.

1. `collect.py`: collect the group list.
2. `analyze.py`: fetch messages, compute participation, and classify each group.
3. `report.py`: generate the Markdown list.

Deliver `report.md`. Highlight **Actively contributing** and **Needs my response**. Present **Can leave** separately as candidates for the user's review, never as authorization to leave groups automatically.

### Platforms and exact rules

Lark (`--source lark`, default) supports full classification. The current WeCom adapter (`--source wecom`) supports session inventory only; analysis is blocked because it cannot read messages. DingTalk and personal WeChat have no supported full adapter. Explain that message-history access is the constraint. See [adapter notes](docs/adapters.md#english-notes).

Apply the first matching rule, in this order:

1. **我在推进 / Actively contributing:** at least 3 user messages and the latest user message within 14 days.
2. **需我响应 / Needs my response:** at least 1 mention of the user within 7 days and group activity within 14 days.
3. **我在关注 / Following:** group activity within 30 days, or an inactive group where the user spoke within 60 days.
4. **无需处理 / No action needed:** the user has participated and the group has activity within 90 days.
5. **可退出 / Can leave, after review:** silence beyond 90 days, no participation in an inactive group, or no readable messages.

Read [the method notes](docs/method.md#english-notes) for caveats. Change `CONFIG` only when deliberately changing thresholds.

### Delivery caveats and troubleshooting

Explain that client-side archiving and bulk departure are not automated by this workflow. Classification is an inference about observed behavior, not a judgment of business importance. Ask the user to review the results.

- Non-JSON message response: the script retries once; persistent failure is marked `unknown`.
- Unrecognized user messages: display-name changes or duplicates may be responsible; prefer `--me-id`.
- Invalid page size: keep message requests at or below 50.
- Slow analysis: each group needs a request; `--sleep 0` reduces delay but may encounter rate limits.
- No readable messages: new or announcement-only groups can be placed in **Can leave** and must be reviewed manually.

Never commit real `data/` or `report.md` to a public repository. Both are excluded by `.gitignore`.
