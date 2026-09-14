<div align="center">

# <img src="engine/docs/images/avatar.png" width="36" height="36" alt="" style="vertical-align:middle;border-radius:50%" /> Blink

[![Update Rule-Sets](https://github.com/byyoshen/Blink/actions/workflows/update.yml/badge.svg?branch=main)](https://github.com/byyoshen/Blink/actions/workflows/update.yml)
[![Portal](https://img.shields.io/badge/Portal-网页入口-4d6bfe?style=flat-square)](https://byyoshen.github.io/Blink/)
[![License: MIT](https://img.shields.io/github/license/byyoshen/Blink?style=flat-square)](LICENSE)

</div>

个人使用的**多客户端规则与配置文件**仓库，分两层：

- **规则层（自动维护）** —— 把经过审计的上游规则编译为一份 canonical 规则，渲染成
  **Surge / Shadowrocket / Loon / Stash / mihomo / Egern / Quantumult X** 七种客户端格式，
  每日更新。不是为每个客户端各维护一套规则。
- **配置层（人工维护）** —— 把同一份配置意图（策略组 / 规则引用 / 通用设置）迁移为七客户端
  **完整配置文件**，单一订阅池、订阅占位符已内置。

生成目录由构建器维护，**不允许手工修改**；仓库不含任何订阅 URL、token、密码或证书。

> [!IMPORTANT]
> 仅供个人学习研究使用。使用前请阅读 [DISCLAIMER.md](DISCLAIMER.md) 与
> [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)；**禁止以任何形式转载或发布至国内平台**。

## 目录

- [规则集](#规则集)
- [语义分段视图](#语义分段视图)
- [配置文件](#配置文件)
- [网页入口](#网页入口)
- [完整性校验](#完整性校验)
- [来源政策](#来源政策)
- [常见问题](#常见问题)
- [使用与许可](#使用与许可)

## 规则集

规则集文件**不带策略名**，policy 由引用处指定。七端引用方式：

| 客户端 | 配置段 | 引用方式 | 分发目录 |
| --- | --- | --- | --- |
| Surge | `[Rule]` | `RULE-SET,<URL>,<策略>` | `Surge/` |
| Shadowrocket | `[Rule]` | `RULE-SET,<URL>,<策略>` | `Shadowrocket/` |
| Loon | `[Remote Rule]` | `URL, policy=<策略>, tag=<App>, enabled=true` | `Loon/` |
| Stash | `rule-providers` + `rules` | `RULE-SET,<App>,<策略>` | `Stash/` |
| mihomo | `rule-providers` + `rules` | `RULE-SET,<App>,<策略>` | `mihomo/` |
| Egern | `rules` | `rule_set: {match: <URL>, policy: <策略>}` | `Egern/` |
| Quantumult X | `[filter_remote]` | `URL, tag=<App>, force-policy=<策略>, …` | `QuantumultX/` |

`Surge/`、`Loon/`、`Shadowrocket/`、`Stash/` 四份内容**逐字节相同**，取自己客户端的目录即可。
`mihomo/` 是同一份内容去掉 `USER-AGENT` 行（Clash 系内核无此类型）—— 构建器显式丢弃并计数，
不静默转换。

需要多行配置的三个客户端：

**Stash**

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

**mihomo**（Clash Meta for Android / FLClash）

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

**Egern**

```yaml
rules:
  - rule_set:
      match: https://raw.githubusercontent.com/byyoshen/Blink/main/Egern/<App>.yaml
      policy: <你的策略>
```

其余四端各加一行。**下面每段属于一个客户端，不要混进同一份配置。**

**Surge / Shadowrocket** —— `[Rule]` 段，`FINAL` 之前：

```ini
RULE-SET,https://raw.githubusercontent.com/byyoshen/Blink/main/Surge/<App>.list,<你的策略>
```

**Loon** —— `[Remote Rule]` 段：

```ini
https://raw.githubusercontent.com/byyoshen/Blink/main/Loon/<App>.list, policy=<你的策略>, tag=<App>, enabled=true
```

**Quantumult X** —— `[filter_remote]` 段：

```ini
https://raw.githubusercontent.com/byyoshen/Blink/main/QuantumultX/<App>.list, tag=<App>, force-policy=<你的策略>, update-interval=172800, opt-parser=false, enabled=true
```

> raw 直连不稳时可改用 jsDelivr（缓存最长 12 小时，规则更新相应延迟）：
> `https://cdn.jsdelivr.net/gh/byyoshen/Blink@main/Surge/<App>.list`，其余目录同理替换。

> **路径变更（2026-09-13）**：`Clash/` 已改为 `mihomo/`，`Profiles/Clash.yaml` 已改为
> `Profiles/mihomo.yaml`。旧 `/Clash/` raw URL 不再可用。

## 语义分段视图

除完整 `.list` 外，每个 App 按语义派生 domain-first / IP-last 的分段视图，供需要控制解析
时机与顺序的场景引用：

| 视图 | 内容 | 引用方式（Surge / Shadowrocket） | 触发 DNS |
| --- | --- | --- | --- |
| `<App>-domainset.conf` | 纯域名裸清单（`DOMAIN` / `DOMAIN-SUFFIX`） | `DOMAIN-SET,<URL>,<策略>,extended-matching` | 否 |
| `<App>-nonip.conf` | 非 IP 规则行（`DOMAIN,` / `DOMAIN-SUFFIX,` / `DOMAIN-KEYWORD,` / `USER-AGENT,` / `PROCESS-NAME,`） | `RULE-SET,<URL>,<策略>` | 否 |
| `<App>-ip.conf` | IP 规则行（`IP-CIDR,` / `IP-CIDR6,`） | `RULE-SET,<URL>,<策略>,no-resolve` | **是** |

两点必须记住：

1. **`domainset` 与 `nonip` 互斥** —— 非 IP 部分全部是域名时产出 `-domainset.conf`，含
   keyword / UA / PROCESS 时产出 `-nonip.conf`，同一 App 只会得到其中之一。空视图不产出，
   纯域名 App 没有 `-ip.conf`。
2. **引用类型由文件后缀决定** —— `-domainset.conf` 配 `DOMAIN-SET`，`-nonip.conf` 与
   `-ip.conf` 配 `RULE-SET`。写反后 Surge **不会报错**，该规则集只是不生效、流量悄悄落到
   `FINAL`；分流不符预期时先查这一项。

**顺序不变式：所有域名段必须置于所有 IP 段之前，没有例外。** 客户端匹配 IP 规则前必须先解析
域名，顺序写反会让待代理域名被本地提前解析，失去 DNS 防污染保护。理由、后果与守它的门禁见
[`engine/docs/DNS_SEMANTICS.md`](engine/docs/DNS_SEMANTICS.md)。

门户复制出来的是 raw 地址（Stash / mihomo 例外，给的是完整 `rule-providers` 片段），
不要自行改写引用类型。

## 配置文件

七客户端**完整配置文件**位于 [`Profiles/`](Profiles/)：`Surge.conf`、`Shadowrocket.conf`、
`Loon.conf`、`Stash.yaml`、`mihomo.yaml`、`Egern.yaml`、`QuantumultX.conf`。

1. 下载对应客户端的配置文件，或在[门户](https://byyoshen.github.io/Blink/)「配置文件」板块用
   **iOS 一键导入**（mihomo 是 Android 客户端，手动导入）。
2. 把 `https://YOUR-SUBSCRIPTION-URL` 替换成你的订阅链接。
3. 导入客户端，真机验证策略组与分流效果。

**人工维护层**：配置文件不随规则每日更新。唯一入口是
[`engine/sources/profile/intent.yaml`](engine/sources/profile/intent.yaml) 与 templates，
改后运行 `engine/scripts/build_profile.py --write` 重建，人工确认后提交。

## 网页入口

[`https://byyoshen.github.io/Blink/`](https://byyoshen.github.io/Blink/) —— 规则集、接入片段、
配置文件（含 iOS 一键导入）与构建来源四个板块，七客户端可切换，规则数与接入片段一键复制。

## 完整性校验

根目录 [`manifest.json`](manifest.json) 为 30 个 App 的 **210 个主产物与 266 个语义视图**记录
SHA256、上游内容指纹、canonical 规则指纹，以及显式降级与 exclude 命中统计。

push / PR 与每日更新自动执行门禁：单元与回归、七端等价性、产物健康度、语义视图一致性、
跨 App overlap、产物溯源、Profile 完整性、门户数据同步、仓库身份一致性与敏感模式。
完整命令与设计边界见 [`engine/docs/MACHINE_GATES.md`](engine/docs/MACHINE_GATES.md)。

## 来源政策

- 每个 App 独立审计选源，以更新活跃度、覆盖完整度、范围精准度、格式适合度与维护质量为证据；
  作者偏好（SukkaW > Repcz > 其他长期验证的成熟作者）只在候选规范化后等价时作 tie-breaker。
  每 App 恰好 1 个 primary、至多 1 个 supplemental。完整候选、证据与结论见
  [`engine/SOURCE_AUDITS.md`](engine/SOURCE_AUDITS.md)。
- Reject / Domestic / China IP / CDN / LAN 等基础设施**不复制进本仓库**，继续直接引用成熟上游。

## 常见问题

**这是什么？** 一份 canonical 规则渲染成七种客户端格式的规则集，外加人工维护的完整配置文件。
不是代理客户端，不负责你的策略。

**为什么各客户端规则数不一样？** 显式降级，不是缺漏：Egern / Quantumult X 丢弃
`PROCESS-NAME`，mihomo 丢弃 `USER-AGENT`。计数见门户卡片与构建报告。

**规则多久更新？** 每日自动更新（约北京时间 00:01），有变化才提交。客户端侧的刷新节奏由引用行
的 `interval` 决定：Stash / mihomo 1 天、Quantumult X 2 天、其余由客户端自行更新。

**出问题了怎么反馈？** 先自检引用类型与顺序（见[语义分段视图](#语义分段视图)），以及目标是否属
基建类（Reject / Domestic / CDN / China IP / LAN，有意不收录）。确属漏网请附客户端 + 日志确认的
域名 + 与上游比较的结果，或按[规则反馈模板](.github/ISSUE_TEMPLATE/rule-feedback.md)提交。
个人仓库无响应承诺 —— 带证据的反馈最快修复。

**我能参与维护吗？** 规则由作者本人维护。带证据的建议与反馈永远欢迎；Pull Request 是否采纳、
何时响应，由作者决定。

## 使用与许可

感谢上游作者对规则集的长期维护（各 App 的来源明细与
许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)）。

本仓库为个人规则分发与学习维护而设，无任何担保；请结合自己的客户端策略与日志自行验证，并遵守
适用法律、服务条款与上游许可。原创部分（构建代码、测试、工作流、门户源码与文档）以
[MIT License](LICENSE) 授权；`Surge/`、`Loon/`、`Shadowrocket/`、`Stash/`、`mihomo/`、`Egern/`、
`QuantumultX/` 与 `Profiles/` 等生成产物**不在 MIT 覆盖范围内**，逐文件遵循
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 记载的上游许可。
