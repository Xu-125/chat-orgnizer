# 群聊整理器 · chat-orgnizer

**English.** A small CLI that sorts your Feishu (Lark) group chats by *your own behavior in them*, not by what each chat is nominally "for". It reads the recent messages of every group you're in, counts how often **you** speak, how often **you** get @-mentioned, and how active the chat is overall, then buckets every group into one of five tiers:

- **active** — you're driving it, check daily
- **respond** — someone just @-mentioned you, reply soon
- **watching** — relevant, but you're mostly lurking
- **idle** — nothing needed from you
- **quit** — project's over / chat's dead, you can leave

It can also tag groups by **project** (a book launch, a live stream, a documentary shoot) so the same 200+ chats can be sliced as "what am I actually working on this week", on top of the engagement tiers. Runs entirely on your machine with the official Lark CLI — no server, no dashboard, no "open this app to see your groups".

---

把飞书里被拉进去的一大堆群，按「你实际投入了多少」分成五档，然后落成一份可用的清单。

解决三件具体的事：

- 被临时拉进群，进去不知道自己要干嘛
- 项目结束群就荒废，长期没人说话
- 群多到不可能逐个点开看

## 为什么按「你的行为」分，不按「群的性质」分

按群的性质分（项目群 / 通知群 / 临时群 / 长期团队）看着整齐，但对你没用。一个标着"重要项目"的群，你可能三个月没发过一句话；一个叫"XX 通知"的群，你天天在里面被 @。

所以这里只用你自己产生的数据做判断：**你在这个群发过多少条、最后一次说话是什么时候、最近被 @ 了几次、群本身还活不活**。同样的群名、同样的团队，落到哪个档位由你的行为决定，不由群的名字决定。

## 现在支持哪些平台

表里分两层看：**接口层**是平台开放了什么能力（跟用谁的机器无关）；**本机要准备**是运行时探测的环境状态（CLI 装没装、登没登，换台机器装好就能用）。

| 平台 | 接口层：群列表 | 接口层：历史消息 | 本机要准备 |
|---|---|---|---|
| 飞书 | ✅ | ✅ | 装好并以用户身份登录 `lark-cli` |
| 企业微信 | ⚠️ 只能列会话 | ❌ 消息内容接口未开放 | 装好并授权 `wecom-cli`；即使授权也只能列群、读不到消息 |
| 钉钉 | 仓库内未接 | 仓库内未接 | 需要先有企业内部应用和群会话读取权限，再补对应适配器 |
| 个人微信 | ❌ 无官方 API | ❌ | 不接非官方协议或模拟点击 |

**只有群列表、没有消息，就只能盘点"我在多少个群"，算不出"我在这个群投入多少"。** 所以企业微信目前只到列群这一层；`analyze.py` 在检测到平台不支持读消息时会直接拦住，不会产出一份全是「可退出」的假结果。

CLI 是否安装、是否已授权，由脚本启动时探测：找不到命令会直接退出并给安装指引，不会当成平台不支持。接入方式和各平台的权限门槛见 [docs/adapters.md](docs/adapters.md)。

## 五个档位

| 档位 | 判定依据 | 你要做什么 |
|---|---|---|
| 我在推进 | 近 14 天有发言，且发言条数够多，你在主导 | 每天看一眼，有事当天回 |
| 需我响应 | 近 7 天被 @ 或被人点名，群仍活跃 | 尽快回，别让对方等 |
| 我在关注 | 群还活着、信息与你相关，但你基本潜水 | 有空扫一眼，不用回 |
| 无需处理 | 你 60 天以上不发言也不被需要，但入口还有价值（值班号、服务台） | 不用管，留在侧边栏 |
| 可退出 | 项目已收尾、群死寂 90 天以上、或你从头到尾没参与 | 确认后可以退 |

阈值全部集中在 `scripts/analyze.py` 顶部的 `CONFIG`，可以按自己的节奏改。

## 怎么跑

前置：本机装好 `lark-cli` 并且已登录（用用户身份，不是机器人）。

```bash
# 确认能拉到群列表
lark-cli im +chat-list --as user --page-size 1 --format json

# 1. 拉群列表（--source 默认 lark；企业微信写 --source wecom，只能列群）
python scripts/collect.py --source lark --out data/chats_raw.json

# 2. 逐群统计参与度并分档
#    --me 填你在飞书里的显示名；知道 open_id 的话用 --me-id 更准
python scripts/analyze.py --input data/chats_raw.json --me "你的显示名" --out data/chats_analyzed.json

# 3. 出清单
python scripts/report.py --input data/chats_analyzed.json --out report.md
```

时间成本：200 个群大约 10–20 分钟，主要花在逐群拉消息上（每个群 1–2 次请求）。想先小规模试，加 `--limit 10`。

## 跑完拿到什么

- `report.md`：五档总览 + 每个群的分组清单 + 每群的判定依据（为什么它在这档）
- `data/chats_analyzed.json`：结构化结果，字段足够直接写进多维表格做看板
- 侧边栏分组的建议名单：按五档归好的 `chat_id`，拿去建飞书侧边栏分组

## 仓库结构

```
scripts/
  collect.py          拉群列表（--source 选平台）
  analyze.py          逐群统计，按 CONFIG 里的阈值分档
  projects.py         按项目给群打标签（配置见 examples/projects.example.json）
  report.py           生成 Markdown 清单
  adapters/
    base.py           适配器协议 + 统一数据结构 + CLI 调用工具
    lark.py           飞书：群列表 + 消息（完整）
    wecom.py          企业微信：仅会话列表
docs/
  method.md           判定口径、四类误判、接口边界
  adapters.md         各平台支持情况与接入方式
examples/             8 个虚构群，演示输出长什么样
SKILL.md              给 agent 用的执行说明
```

## 一件做不到的事，先说清

**飞书的群归档是客户端操作，OpenAPI 没有开放 archive 接口。** 所以"长期不用自动归档"做不到全自动。这套东西能自动的环节是：识别哪些群该处理、打上标记、归进哪个分组、定期提醒你。最后点归档或退群那一下，仍然要你在飞书里手动完成。脚本不会假装这件事能自动做。

同理，飞书没有批量退群接口，`可退出` 那一档只能给你一张清单，退群要自己点。

## 隐私

仓库里不含任何真实群名、群 ID、成员信息或个人发言统计。`examples/` 下全部是虚构样例，只用来演示输出长什么样。你本地跑出来的 `data/` 默认在 `.gitignore` 里，不会误传。

## License

MIT

---

## English guide

### What it helps with

Turn the many Lark groups you have been added to into a usable, five-tier list based on **your actual involvement**. It addresses three everyday problems:

- You are added to a group without knowing what you are expected to do.
- Finished project groups sit idle in your chat list.
- There are too many groups to review one by one.

### Why participation, not group type?

Labels such as “project,” “announcement,” or “team” may look tidy, but they do not tell you what needs your attention. You may never speak in an “important project” group while being mentioned daily in an “announcements” group.

The organizer uses your message count, your most recent message, recent mentions of you, and the group's latest activity. Group names do not determine the tier.

### Platform support

- **Lark / Feishu:** group lists and message history through `lark-cli`; full classification works once the CLI is installed and you are signed in as a user.
- **WeCom:** the adapter can list sessions and their latest message times, but cannot read message content. Inventory only; analysis is blocked.
- **DingTalk:** no adapter is bundled yet. Integration requires an enterprise application and authorized group-list/message access; add an adapter following the same interface.
- **Personal WeChat:** not supported; there is no official API.

Whether a CLI is installed and signed in is a local-machine state checked at runtime, not a fixed claim about the platform. A missing command exits with an install hint rather than being treated as unsupported.

A group list alone cannot establish your involvement. The analyzer refuses unsupported message sources rather than returning a misleading list of “can leave” groups. See [platform adapters](docs/adapters.md#english-notes).

### The five tiers

- **我在推进 — Actively contributing:** you have spoken recently and contributed enough messages to indicate active involvement. Check daily and respond the same day when needed.
- **需我响应 — Needs my response:** you were mentioned recently and the group is still active. Respond promptly.
- **我在关注 — Following:** the group still has activity, but you mostly read rather than speak. Review when convenient; a reply is not automatically required.
- **无需处理 — No action needed:** little current involvement, but keeping the group may preserve a useful access point. Leave it available without routine attention.
- **可退出 — Can leave, after review:** an inactive or unused group worth considering for departure. Review it yourself before leaving.

These are behavioral suggestions, not business-importance judgments. Exact rules and known misclassifications are documented in [the method guide](docs/method.md#english-notes). Tune thresholds in `CONFIG` at the top of `scripts/analyze.py`.

### Run it

Prerequisite: install `lark-cli` and authenticate as a **user**, not a bot.

```bash
# Check access to the group list
lark-cli im +chat-list --as user --page-size 1 --format json

# 1. Collect groups (default source: lark; wecom supports inventory only)
python scripts/collect.py --source lark --out data/chats_raw.json

# 2. Analyze participation; replace the name with your actual Lark display name
# Use --me-id instead if you know your open_id; it is more reliable
python scripts/analyze.py --input data/chats_raw.json --me "Your Lark display name" --out data/chats_analyzed.json

# 3. Generate the report
python scripts/report.py --input data/chats_analyzed.json --out report.md
```

The existing guide estimates about 10–20 minutes for 200 groups, mostly spent fetching messages. Actual time depends on the environment and API responses. Add `--limit 10` to the analysis command for a small trial.

### Outputs and repository layout

- `report.md`: tier overview, grouped chat list, and the reason for each classification.
- `data/chats_analyzed.json`: structured results suitable for downstream dashboards.
- Grouped `chat_id` values: suggested input for organizing your Lark sidebar.

```text
scripts/
  collect.py          Collect group lists; select a platform with --source
  analyze.py          Analyze each group and apply CONFIG thresholds
  report.py           Generate a Markdown report
  adapters/
    base.py           Adapter protocol, normalized data, and CLI helpers
    lark.py           Lark group lists and message history
    wecom.py          WeCom session inventory only
docs/
  method.md           Classification rules, failure cases, and API boundaries
  adapters.md         Platform support and integration notes
examples/             Eight fictional groups showing the output format
SKILL.md              Execution instructions for an agent
```

### Limits and privacy

The current workflow does not automate Lark client-side archiving or bulk departure. It identifies and labels candidates; you make the final decision and perform the client action. No script should promise automatic archiving or leaving.

This repository contains no real group names, IDs, member details, or personal participation statistics. All examples are fictional. Local `data/` is excluded by `.gitignore`; do not publish your generated data or reports.

**License:** MIT.
