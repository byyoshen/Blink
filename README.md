<div align="center">

# Blink

**从一条规则，到整份配置。**

[![Portal](https://img.shields.io/badge/Portal-网页入口-4d6bfe?style=flat-square)](https://blink.wendylala.com/)
[授权与第三方许可](LICENSE)

</div>

Blink 是面向八种代理客户端的分流规则与配置文件。它把按 App 审计过的规则编译为一份 canonical 规则，渲染成各客户端的原生格式，并提供可直接导入的完整配置文件。

> [!IMPORTANT]
> 仅供个人学习研究使用。使用前请阅读 [DISCLAIMER.md](DISCLAIMER.md) 与 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
> **禁止以任何形式转载或发布至国内平台。**

## 目录

- [简介](#简介)
- [快速开始](#快速开始)
- [规则集](#规则集)
- [语义分段视图](#语义分段视图)
- [配置文件](#配置文件)
- [规则来源与更新](#规则来源与更新)
- [兼容性](#兼容性)
- [完整性校验](#完整性校验)
- [仓库结构](#仓库结构)
- [常见问题](#常见问题)
- [许可与免责](#许可与免责)

## 简介

### Blink 是什么

- **规则集**：按 App 划分的分流规则，一份 canonical 规则渲染为 Surge、Shadowrocket、Loon、Stash、mihomo、Egern、Quantumult X、sing-box 八种格式。
- **配置文件**：八个客户端各一份完整配置（[`Profiles/`](Profiles/)），人工维护，策略组结构一致。
- **唯一规则来源**：其他作者的清单、厂商公开数据和 Surge 日志都是原料。每条规则是否收录，由 Blink 决定。
- **网页入口**：[blink.wendylala.com](https://blink.wendylala.com/) 提供规则查询、接入片段生成和配置文件导入。

### Blink 不是什么

- 不是代理客户端，不提供网络接入服务。
- 不决定使用者的策略。规则集不带策略名，策略由引用处指定。
- 不收录 Reject、Domestic、China IP、CDN、LAN 等基础设施规则。这些规则直接引用成熟上游。
- 不追求规则数量。范围精准优先，共享 CDN 与云主机不收录。
- 不含个人配置。仓库不含订阅链接、token、密码或证书。

### 覆盖范围

- 范围：经过审计的 App 专项规则，以及经 Surge 日志或实际使用确认的补充规则。
- 收录的 App 清单以 [`manifest.json`](manifest.json) 为准。
- 规则正确性目前通过 Surge 日志验证。其余客户端的规则由同一份 canonical 规则渲染。

### 不作承诺

- 不保证任何规则准确、完整、及时，或适用于特定网络、账号与服务。
- 不保证上游变化、DNS 行为与 App 域名变更后分流结果不变。
- 不承诺响应 Issue 与 Pull Request。

## 快速开始

1. 打开[门户](https://blink.wendylala.com/)，选择客户端与需要的 App。
2. 复制生成的接入片段，粘贴到客户端配置。
3. 需要整份配置时，在门户「配置文件」板块导入，或从 [`Profiles/`](Profiles/) 下载。

不使用门户时，按下文「规则集」直接引用 raw 地址。

## 规则集

规则集文件**不带策略名**，策略由引用处指定。

| 客户端 | 配置段 | 引用方式 | 目录 |
| --- | --- | --- | --- |
| Surge | `[Rule]` | `RULE-SET,<URL>,<策略>` | `Surge/` |
| Shadowrocket | `[Rule]` | `RULE-SET,<URL>,<策略>` | `Shadowrocket/` |
| Loon | `[Remote Rule]` | `URL, policy=<策略>, tag=<App>, enabled=true` | `Loon/` |
| Stash | `rule-providers` + `rules` | `RULE-SET,<App>,<策略>` | `Stash/` |
| mihomo | `rule-providers` + `rules` | `RULE-SET,<App>,<策略>` | `mihomo/` |
| Egern | `rules` | `rule_set: {match: <URL>, policy: <策略>}` | `Egern/` |
| Quantumult X | `[filter_remote]` | `URL, tag=<App>, force-policy=<策略>, …` | `QuantumultX/` |
| sing-box | `route.rule_set` + `route.rules` | `{"rule_set": ["<App>"], "outbound": "<出站>"}` | `SingBox/` |

**目录关系**

- `Surge/`、`Loon/`、`Shadowrocket/`、`Stash/` 四个目录的内容逐字节相同。
- `mihomo/` 与它们相同，但去掉 `USER-AGENT` 行。Clash 系内核没有该类型，构建器显式丢弃并计数，不做静默转换。
- `Egern/` 与 `QuantumultX/` 丢弃 `PROCESS-NAME`，sing-box 丢弃 `USER-AGENT`。丢弃数记录在 `manifest.json`。
- `Clash/` 目录已更名为 `mihomo/`，旧 raw 地址不再可用。

**引用片段**

下面每段属于一个客户端，不要混进同一份配置。

Surge / Shadowrocket：`[Rule]` 段，`FINAL` 之前。

```ini
RULE-SET,https://raw.githubusercontent.com/byyoshen/Blink/main/Surge/<App>.list,<你的策略>
```

Loon：`[Remote Rule]` 段。

```ini
https://raw.githubusercontent.com/byyoshen/Blink/main/Loon/<App>.list, policy=<你的策略>, tag=<App>, enabled=true
```

Quantumult X：`[filter_remote]` 段。

```ini
https://raw.githubusercontent.com/byyoshen/Blink/main/QuantumultX/<App>.list, tag=<App>, force-policy=<你的策略>, update-interval=172800, opt-parser=false, enabled=true
```

Stash：

```yaml
rule-providers:
  <App>:
    type: http
    behavior: classical
    format: text
    url: https://raw.githubusercontent.com/byyoshen/Blink/main/Stash/<App>.list
    interval: 86400
rules:
  - RULE-SET,<App>,<你的策略>
```

mihomo（Clash Meta for Android / FLClash）：

```yaml
rule-providers:
  <App>:
    type: http
    behavior: classical
    format: text
    url: https://raw.githubusercontent.com/byyoshen/Blink/main/mihomo/<App>.list
    interval: 86400
rules:
  - RULE-SET,<App>,<你的策略>
```

Egern：

```yaml
rules:
  - rule_set:
      match: https://raw.githubusercontent.com/byyoshen/Blink/main/Egern/<App>.yaml
      policy: <你的策略>
```

sing-box：`route` 段。格式为 source JSON，`version: 2`。带 IP 的 App 另有 `-ip.json`，其路由规则放在所有域名段之后。

```json
{
  "route": {
    "rule_set": [
      { "tag": "<App>", "type": "remote", "format": "source", "url": "https://raw.githubusercontent.com/byyoshen/Blink/main/SingBox/<App>.json" }
    ],
    "rules": [{ "rule_set": ["<App>"], "outbound": "<你的出站>" }]
  }
}
```

> raw 直连不稳定时，可改用 jsDelivr。缓存最长 12 小时，规则更新相应延迟。
> `https://cdn.jsdelivr.net/gh/byyoshen/Blink@main/Surge/<App>.list`，其余目录同理替换。

## 语义分段视图

除完整 `.list` 外，每个 App 另有 domain-first、IP-last 的分段视图。需要控制解析时机与顺序时引用。

| 视图 | 内容 | 引用方式（Surge / Shadowrocket） | 触发 DNS |
| --- | --- | --- | --- |
| `<App>-domainset.conf` | 纯域名清单（`DOMAIN` / `DOMAIN-SUFFIX`） | `DOMAIN-SET,<URL>,<策略>,extended-matching` | 否 |
| `<App>-nonip.conf` | 非 IP 规则行（`DOMAIN` / `DOMAIN-SUFFIX` / `DOMAIN-KEYWORD` / `USER-AGENT` / `PROCESS-NAME`） | `RULE-SET,<URL>,<策略>` | 否 |
| `<App>-ip.conf` | IP 规则行（`IP-CIDR` / `IP-CIDR6`） | `RULE-SET,<URL>,<策略>,no-resolve` | 是 |

使用时遵守三条规则：

1. **`domainset` 与 `nonip` 互斥。** 非 IP 部分全是域名时，只产出 `-domainset.conf`。含 keyword、UA 或 PROCESS 时，只产出 `-nonip.conf`。空视图不产出，纯域名 App 没有 `-ip.conf`。
2. **引用类型由文件后缀决定。** `-domainset.conf` 配 `DOMAIN-SET`。`-nonip.conf` 与 `-ip.conf` 配 `RULE-SET`。写反时 Surge 不报错，规则集只是不生效，流量落到 `FINAL`。
3. **所有域名段置于所有 IP 段之前，没有例外。** 客户端匹配 IP 规则前需要先解析域名。顺序写反会让应走代理的域名被本地提前解析。原因与操作见 [DNS 与规则顺序](https://github.com/byyoshen/Blink/blob/main/docs/DNS.md)。

## 配置文件

[`Profiles/`](Profiles/) 提供八个客户端的可导入基线配置。

| 客户端 | 文件 |
| --- | --- |
| Surge | `Surge.conf` |
| Shadowrocket | `Shadowrocket.conf` |
| Loon | `Loon.conf` |
| Stash | `Stash.yaml` |
| mihomo | `mihomo.yaml` |
| Egern | `Egern.yaml` |
| Quantumult X | `QuantumultX.conf` |
| sing-box | `SingBox.json` |

**策略组结构**（八个文件一致）

- `Sub`：单一订阅池，包含导入的全部出站。
- `HK`、`TW`、`JP`、`US`、`SG`：按地区筛选 `Sub`。
- `Auto`：在地区组中自动选延迟最低者。
- `Proxy`：地区组 + `Final`。
- `Final`：兜底，地区组 + `Auto` + `Sub` + `DIRECT`。
- App 组：Telegram、X、Instagram（含 Threads）、Youtube、AI、Google、GitHub、Finance（OKX、PayPal）。每组可选地区组与 `Final`（AI 组不含 `SG`）。
- 固定指向：Netflix 与 TikTok 走 `JP`，Spotify 走 `HK`。国内流量直连。

**使用步骤**

1. 下载对应客户端的配置文件，或在门户「配置文件」板块导入。除 Quantumult X 外，门户为各客户端提供一键导入；Quantumult X 需复制配置链接后手动导入。
2. 把 `https://YOUR-SUBSCRIPTION-URL` 替换为自己的订阅链接。
3. sing-box 官方内核没有订阅功能。把 `SingBox.json` 里的占位出站（`HK-01` 等）换成自己的出站。
4. 导入客户端，验证策略组与分流效果。

**边界**

- 配置文件由维护者人工维护，不随规则自动重建。
- 只含核心策略组与常用 App 的规则，其余 App 自行添加。
- 基础设施规则（广告拦截、国内直连、局域网等）以远程引用方式指向成熟上游，不复制规则内容。
- 不含任何个人信息、订阅链接或密钥。

## 规则来源与更新

**来源**

- Blink 是唯一规则来源。其他清单是原料，来源与许可记录在 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
- 每个 App 经审计选定一份主要原料。证据包括更新活跃度、覆盖完整度、范围精准度、格式适合度与维护质量。没有现成清单的 App 依靠 Surge 日志。
- 技术依据：各客户端的官方文档、规则匹配与 DNS 等领域的官方规范、社区讨论与公开技术文档（如 [SukkaW](https://github.com/SukkaW/Surge) 的 Surge 文档），以及维护者自己的专业判断。

**收录与退休**

- 收录：至少两家独立清单都有（同一作者的副本只算一票），或有厂商公开数据、Surge 日志佐证。
- 不收：共享基础设施（CDN、云主机）。
- GPL / AGPL 清单只作佐证，不直接收录其条目。
- 退休：所有清单都没有、域名无法解析、日志 90 天未出现，且连续两个月成立。退休可以恢复。

**更新节奏**

| 动作 | 频率 | 说明 |
| --- | --- | --- |
| 规则更新 | 每月 1 日 | 比对全部原料，收下新规则，退休失效规则。维护者确认后发布。 |
| 原料检查 | 每日（约北京时间 00:01） | 只检查原料能否读取，不改规则。结果见 [`status.json`](https://raw.githubusercontent.com/byyoshen/Blink/status/status.json)。 |
| 客户端刷新 | 由引用行决定 | Stash / mihomo 1 天，Quantumult X 2 天，其余由客户端自行更新。 |

## 兼容性

- 八个客户端均需使用当前稳定版本。除 sing-box 外，没有官方文档给出最低版本。
- sing-box：规则集文件需要 1.10.0 或以上。使用 `REJECT` 时，路由片段需要 1.11.0 或以上。
- mihomo 配置以 1.19.32 内核做检查，尚未验证最低版本。

## 完整性校验

根目录 [`manifest.json`](manifest.json) 记录每个 App 主产物与语义视图的 SHA256、上游内容指纹、canonical 规则指纹，以及显式丢弃与 exclude 的命中统计。

发布前的门禁包括：单元与回归、多端等价性、产物健康度、语义视图一致性、跨 App 重叠、产物溯源、配置文件完整性、仓库身份一致性与敏感内容扫描。这些检查在私有引擎仓库中执行。公开 manifest 中的产物哈希可独立核对。

## 仓库结构

| 路径 | 内容 |
| --- | --- |
| `Surge/` `Shadowrocket/` `Loon/` `Stash/` `mihomo/` `Egern/` `QuantumultX/` `SingBox/` | 各客户端规则集与语义视图 |
| `Profiles/` | 八个客户端的完整配置文件 |
| `manifest.json` | 产物哈希、指纹与降级统计 |
| `docs/` | [DNS 与规则顺序](docs/DNS.md) |
| `THIRD_PARTY_NOTICES.md` | 原料来源与许可 |
| `DISCLAIMER.md` | 免责说明 |
| `LICENSE` | 授权条款 |

生成目录由构建器维护，**不允许手工修改**。构建引擎、门户源码与审计档案在私有仓库维护，本仓库只接收自动发布。

## 常见问题

**各客户端的规则数为什么不同？**
这是显式降级，不是缺漏。见「规则集」中的目录关系。计数见门户卡片与 `manifest.json`。

**分流没有按预期生效，怎么排查？**
依次检查：

1. 引用类型是否与文件后缀匹配（见[语义分段视图](#语义分段视图)）。
2. 域名段是否全部在 IP 段之前。
3. 目标是否属于有意不收录的基础设施类。

**如何反馈规则问题？**
通过[规则反馈表单](https://github.com/byyoshen/Blink/issues/new?template=rule-feedback.yml)提交。请附带：客户端、日志确认的域名、与上游的比较结果。带证据的反馈处理最快。

**可以参与维护吗？**
规则由作者维护。欢迎带证据的建议与反馈。是否采纳、何时响应，由作者决定。

## 许可与免责

本仓库没有单一许可。适用范围如下，完整条款见 [LICENSE](LICENSE)：

| 内容 | 条款 |
| --- | --- |
| 规则集中的上游材料 | 遵循各上游自己的许可，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |
| Yoshen 原创规则，以及 Profiles 中可单独授权的原创部分 | CC BY-NC-SA 4.0，署名 Yoshen / Blink |
| README 等原创说明文字，门户页面文字与标识 | 保留所有权利 |
| 此前已按 MIT 发布的内容 | 仍按 MIT，本次条款不撤销既有授权 |

CC BY-NC-SA 4.0 不改变上游 GPL / AGPL 等材料的许可。

本仓库按「现状」提供，不附带任何担保。使用者需自行验证规则、选择策略并保护自己的凭据。详见 [DISCLAIMER.md](DISCLAIMER.md)。
