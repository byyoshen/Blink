<div align="center">

# Blink

[![Portal](https://img.shields.io/badge/Portal-网页入口-4d6bfe?style=flat-square)](https://blink.wendylala.com/)
[授权与第三方许可](LICENSE)

</div>

个人使用的**多客户端规则与配置文件**仓库，分两层：

- **规则层（自动维护）** —— 把经过审计的上游规则编译为一份 canonical 规则，渲染成
  **Surge / Shadowrocket / Loon / Stash / mihomo / Egern / Quantumult X / sing-box** 八种客户端格式，
  每日更新。不是为每个客户端各维护一套规则。
- **配置层（人工维护）** —— 把同一份配置意图（策略组 / 规则引用 / 通用设置）迁移为七客户端（sing-box 暂只提供规则集）
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
- [文档地图](#文档地图)
- [使用与许可](#使用与许可)

## 规则集

规则集文件**不带策略名**，policy 由引用处指定。八端引用方式：

| 客户端 | 配置段 | 引用方式 | 分发目录 |
| --- | --- | --- | --- |
| Surge | `[Rule]` | `RULE-SET,<URL>,<策略>` | `Surge/` |
| Shadowrocket | `[Rule]` | `RULE-SET,<URL>,<策略>` | `Shadowrocket/` |
| Loon | `[Remote Rule]` | `URL, policy=<策略>, tag=<App>, enabled=true` | `Loon/` |
| Stash | `rule-providers` + `rules` | `RULE-SET,<App>,<策略>` | `Stash/` |
| mihomo | `rule-providers` + `rules` | `RULE-SET,<App>,<策略>` | `mihomo/` |
| Egern | `rules` | `rule_set: {match: <URL>, policy: <策略>}` | `Egern/` |
| Quantumult X | `[filter_remote]` | `URL, tag=<App>, force-policy=<策略>, …` | `QuantumultX/` |
| sing-box | `route.rule_set` + `route.rules` | `{"rule_set": ["<App>"], "outbound": "<出站>"}` | `SingBox/` |

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

**sing-box** —— `route` 段（source 格式 JSON，`version: 2`，sing-box 1.10.0 起可用；带 IP 的 App 另有 `-ip.json`，其路由规则放在所有域名段之后）：

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
域名，顺序写反会让待代理域名被本地提前解析，失去 DNS 防污染保护。原因与操作说明见
[DNS 与规则顺序](https://github.com/byyoshen/Blink/blob/main/docs/DNS.md)。

门户复制出来的是 raw 地址（Stash / mihomo 例外，给的是完整 `rule-providers` 片段），
不要自行改写引用类型。

## 配置文件

七客户端**可直接导入的基线配置文件**位于 [`Profiles/`](Profiles/)（内置 6 个常用 App 的分流，其余 App 按需自行添加）：`Surge.conf`、`Shadowrocket.conf`、
`Loon.conf`、`Stash.yaml`、`mihomo.yaml`、`Egern.yaml`、`QuantumultX.conf`。

1. 下载对应客户端的配置文件，或在[门户](https://blink.wendylala.com/)「配置文件」板块用
   **iOS 一键导入**（mihomo 是 Android 客户端，手动导入）。
2. 把 `https://YOUR-SUBSCRIPTION-URL` 替换成你的订阅链接。
3. 导入客户端，真机验证策略组与分流效果。

**人工维护层**：配置文件由维护者在私有引擎仓库中生成并审核发布，不随规则每日自动重建。

## 网页入口

[`https://blink.wendylala.com/`](https://blink.wendylala.com/) —— 规则集、接入片段、
配置文件（含 iOS 一键导入）与构建来源四个板块。客户端全站只选一次并会被记住；勾选需要的 App，
接入片段只为它们生成，链接带 `?apps=` 参数可以分享同一组选择。

## 完整性校验

根目录 [`manifest.json`](manifest.json) 为每个 App 的**主产物与语义视图**记录 SHA256、上游内容指纹、
canonical 规则指纹，以及显式降级与 exclude 命中统计（当前数量以该文件为准）。

push / PR 与每日更新自动执行门禁：单元与回归、多端等价性、产物健康度、语义视图一致性、
跨 App overlap、产物溯源、Profile 完整性、门户数据同步、仓库身份一致性与敏感模式。
这些检查在私有引擎仓库中执行；公开 manifest 中的产物哈希可独立核对，私有源码指纹不能仅凭本仓库重建验证。

## 来源政策

- 每个 App 独立审计选源，以更新活跃度、覆盖完整度、范围精准度、格式适合度与维护质量为证据；
  作者偏好（SukkaW > Repcz > 其他长期验证的成熟作者）只在候选规范化后等价时作 tie-breaker。
  有上游的 App 恰好 1 个 primary、至多 1 个 supplemental；没有可用上游的 App 只用本仓库的补充规则。完整候选、证据与结论保留在私有审计档案中，公开来源明细见
  [第三方声明](THIRD_PARTY_NOTICES.md)。
- Reject / Domestic / China IP / CDN / LAN 等基础设施**不复制进本仓库**，继续直接引用成熟上游。

## 常见问题

**这是什么？** 一份 canonical 规则渲染成八种客户端格式的规则集，外加人工维护的完整配置文件。
不是代理客户端，不负责你的策略。

**为什么各客户端规则数不一样？** 显式降级，不是缺漏：Egern / Quantumult X 丢弃
`PROCESS-NAME`，mihomo / sing-box 丢弃 `USER-AGENT`。计数见门户卡片与构建报告。

**规则多久更新？** 每日自动检查上游（约北京时间 00:01），上游有变化才提交。客户端侧的刷新节奏由引用行
的 `interval` 决定：Stash / mihomo 1 天、Quantumult X 2 天、其余由客户端自行更新。

**出问题了怎么反馈？** 先自检引用类型与顺序（见[语义分段视图](#语义分段视图)），以及目标是否属
基建类（Reject / Domestic / CDN / China IP / LAN，有意不收录）。确属漏网请附客户端 + 日志确认的
域名 + 与上游比较的结果，或按[规则反馈表单](https://github.com/byyoshen/Blink/issues/new?template=rule-feedback.yml)提交。
个人仓库无响应承诺 —— 带证据的反馈最快修复。

**我能参与维护吗？** 规则由作者本人维护。带证据的建议与反馈永远欢迎；Pull Request 是否采纳、
何时响应，由作者决定。

## 公开范围

本仓库只分发八客户端规则、七份 Profile、manifest、使用说明与规则反馈表单。
构建引擎、门户源码和审计档案在私有仓库维护；原有公开提交历史保留。
规则与配置继续使用本仓库 `main` 下的原始地址。

- [DNS 与规则顺序](https://github.com/byyoshen/Blink/blob/main/docs/DNS.md)
- [第三方声明](THIRD_PARTY_NOTICES.md) · [免责说明](DISCLAIMER.md) · [授权条款](LICENSE)
- [最近一次每日检查记录](https://raw.githubusercontent.com/byyoshen/Blink/status/status.json)

## 使用与许可

感谢上游作者 SukkaW、Repcz、v2fly、blackmatrix7，还有我自己对规则集的长期维护（各 App 的来源明细与
许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)）。

本仓库为个人规则分发与学习维护而设，无任何担保；请结合自己的客户端策略与日志自行验证。
规则中的上游材料遵循各自许可；Yoshen 原创规则与 Profiles 中可单独授权的原创部分采用
CC BY-NC-SA 4.0；README 等原创说明文字保留所有权利。详细范围见公开仓库的
[LICENSE](https://github.com/byyoshen/Blink/blob/main/LICENSE)。此前已按 MIT 发布的内容仍按 MIT，
此次变更不撤销既有授权，也不将上游 GPL/AGPL 等材料改为非商业许可。
