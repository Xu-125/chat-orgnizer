# 判定口径

这份文档解释脚本在判断什么、为什么这么判断，以及哪些地方容易判错。想调结果的话，先看这里再改 `scripts/analyze.py` 顶部的 `CONFIG`。

## 一、问题定义

一个人被动加入大量群聊，会产生两种损耗：

1. **入群成本**——刚被拉进去，不知道这个群为什么有自己、自己要做什么。
2. **持仓成本**——群结束后没人解散，长期留在列表里，每次扫消息都要多看几眼。

第一种靠读历史消息解决，第二种靠识别"这个群对我已经没用了"。两者的共同前提是：**先知道每个群对你意味着什么**，而这个"意味着什么"不能从群名推。

## 二、两个数据源

| 数据 | 命令 | 用途 |
|---|---|---|
| 群列表 | `lark-cli im +chat-list --as user --page-all --format json` | 拿到全部群和 `chat_id` |
| 群消息 | `lark-cli im +chat-messages-list --chat-id <id> --order desc --page-size 50 --format json` | 算你在这个群的行为 |

消息里的关键字段：

- `sender`：发送者，含 `id`（open_id）和 `name`（显示名）
- `create_time`：发送时间，可能是 `YYYY-MM-DD HH:MM:SS`，也可能是毫秒时间戳，脚本两种都兼容
- `mentions`：被 @ 的人，每项含 `id` / `name`
- `deleted`：是否已撤回，撤回的消息不计入统计

## 三、统计口径

对每个群，统计四个量：

| 字段 | 含义 | 怎么算 |
|---|---|---|
| `my_msgs` | 你在这个群发了多少条 | `sender.id == 你` 或 `sender.name == 你` |
| `my_last` | 你最后一次发言的日期 | 你发出的消息里最大的 `create_time` |
| `at_me` | 被 @ 的次数 | `mentions` 里命中你；另算 `at_me_7d`（最近 7 天） |
| `group_last` | 群最后活跃日期 | 全部消息里最大的 `create_time` |

窗口默认取最近 30 天、每群最多 100 条消息。这个量足够判断"你还活不活跃"，也不需要拉全量历史。

**为什么用"我的行为"当主指标**：群名、群成员构成、群描述都是别人给的标签，会过期；只有"我最近说过话没有"是自己真实发生的。一个人可以待在一个"核心项目群"里三个月不发言，也可以在一个名字不起眼的群里天天被 @。

## 四、五档判定（按优先级从上往下）

```text
1. 我在推进   my_msgs >= 3 且 my_last <= 14 天
2. 需我响应   近 7 天被 @ >= 1 且群 14 天内还有消息
3. 我在关注   群 30 天内还有消息（你在潜水）
              或群已冷，但你 60 天内发过言
4. 无需处理   你在群里参与过，群 90 天内还有零星消息
5. 可退出     群静默超过 90 天 / 你从没发过言且群不动 / 无可读消息
```

优先级的意义：一个群可能同时满足多条（比如你既在推进、又被 @）。按上表顺序取第一个命中项——正在推进的群不需要再提醒你"被 @ 了"，那本来就该看。

## 五、已知的误判类型

**1. 群名像核心群，其实不需要你**

典型的对口长期群：群每天刷屏，但你 90 天没说过一句，几次 @ 都是两三个月前的旧消息。这类会被判「我在关注」，容易被误读成"该回"。判断时以 `at_me_7d` 为准，历史 @ 不算待办。

**2. 群已经结束，但群还在零星响**

项目群收尾后常有人发个文件、问句"这个还要吗"。这种群 `group_last` 可能才 10 天，判成「我在关注」。人工复核时看 `my_last`——如果最后一次是你发的、之后没人接，基本可以退。

**3. 无消息记录的群**

新群、纯通知群可能拉不到消息。脚本直接判「可退出」并标注"没有任何可读消息"。但这批群里往往混着值班号、服务台这类"要留入口"的，所以建议把「可退出」当候选清单，退群前扫一眼群名。

**4. 换过显示名或昵称**

按 `sender.name` 匹配时，改过昵称会导致认不出自己。知道 open_id 就用 `--me-id`，稳定得多。

## 六、做不到的事

| 想做 | 现状 | 替代做法 |
|---|---|---|
| 群自动归档 | 归档是飞书客户端操作，OpenAPI 未开放 | 识别 + 标签 + 归入「可退出」分组 + 定期提醒，最后手动归档 |
| 批量退群 | 无批量退群接口 | 输出退货清单，自己逐条点 |
| 判断群的业务重要性 | 只能从行为推断，读不到业务上下文 | 偶尔人工复核「我在关注」这一档 |

这三点不是实现偷懒，是接口边界。任何声称"能自动帮你归档群"的方案，最后都要落到手动操作上。

## 七、维护节奏

- **每月**跑一次全量。群活跃度漂移很快，一次分类管不了半年。
- **每周**只看「我在推进」「需我响应」两档，其余不看。
- **每季度**清一次「可退出」，集中退一批。
- 有新群进来随时跑单群分析，不用等周期。

---

## English notes

### Problem and data

Being added to many groups creates an onboarding cost—working out why you are there—and a continuing attention cost when finished groups remain in the list. The starting point is understanding what each group means to you, which cannot be inferred from its name alone.

The method uses group lists to obtain `chat_id` values and message history to observe participation. The commands are shown in the Chinese section above. Key message fields are:

- `sender`: user ID and display name.
- `create_time`: a date-time string or millisecond timestamp; both are supported.
- `mentions`: IDs or names of mentioned users.
- `deleted`: withdrawn messages are excluded.

For each group, compute:

- `my_msgs`: messages matching your sender ID or display name.
- `my_last`: the latest timestamp among your messages.
- `at_me`: mentions matching you; `at_me_7d` counts only the last 7 days.
- `group_last`: the latest timestamp across readable messages.

The default window is 30 days, capped at 100 messages per group. Counts represent the fetched window, not necessarily the entire lifetime of the group. Behavioral evidence is preferred to names and descriptions that may be outdated.

### Classification priority

Apply the first matching tier:

1. **Actively contributing (我在推进):** `my_msgs >= 3` and your latest message within 14 days.
2. **Needs my response (需我响应):** at least one mention within 7 days and group activity within 14 days.
3. **Following (我在关注):** activity within 30 days, or a group that has cooled down but where you spoke within 60 days.
4. **No action needed (无需处理):** you have participated and the group still has occasional activity within 90 days.
5. **Can leave, after review (可退出):** silence beyond 90 days, no participation in an inactive group, or no readable messages.

A group can match several conditions. The first match takes precedence; an actively contributing group does not need a separate response-needed classification.

### Known misclassifications

1. **An important-sounding group does not need you:** ongoing group traffic can place it in **Following** even if you have not spoken for months. Only recent `at_me_7d` mentions count as response signals; old mentions are not current tasks.
2. **A finished project still has occasional messages:** a recent `group_last` can keep it in **Following**. Review your last contribution and the actual project status before deciding to leave.
3. **No readable messages:** new or announcement-only groups may be classified as **Can leave**, including service desks or on-call access points you want to retain. Always treat this tier as a candidate list.
4. **Changed or duplicate display names:** matching `sender.name` may miss your messages. Prefer `--me-id` when your ID is known.

### Limits and maintenance

The current workflow does not automate client-side archiving or bulk departure. It identifies candidates and provides a list; the user performs the final client action. It also cannot infer business importance from behavior alone, so occasional manual review of **Following** is useful.

Suggested cadence: run a full inventory monthly; focus weekly on **Actively contributing** and **Needs my response**; review departure candidates quarterly; analyze new groups when needed. Classification changes as activity changes.
