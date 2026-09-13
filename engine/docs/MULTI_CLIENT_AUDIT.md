# Blink Multi-Client Audit（Surge / Shadowrocket / Loon / Stash / Egern / Quantumult X / Clash）

> 审计日期：2026-08。目的：在动手改代码前，确认七个客户端的规则格式事实，
> 决定 Shared Output、Renderer 数量与 Output Architecture。本文件是
> 实现阶段的唯一格式依据；实现若与本文件冲突，先回改本文件再改代码。

## 1. 审计方法与证据层级

开发环境无法直连 HTTP，证据分三层，优先级从高到低：

1. **官方文档**：
   - Surge：[官方手册](https://manual.nssurge.com/rule/ruleset.html) + 官方手册汉化仓库 [lockcp/SurgeHandbook](https://github.com/lockcp/SurgeHandbook)（内容可核对）。
   - Loon：[官方手册仓库 Loon0x00/LoonManual](https://github.com/Loon0x00/LoonManual) + 官方示例配置 [Loon0x00/LoonExampleConfig](https://github.com/Loon0x00/LoonExampleConfig)（内容可核对）。
   - Stash：[Rule Sets](https://stash.wiki/en/rules/rule-set)、[Rule Types](https://stash.wiki/en/rules/rule-types)（页面存在；正文本环境不可读，结论以生产实证为准并标注）。
   - Egern：[Rules](https://egernapp.com/docs/configuration/rules)（正文本环境不可读，结论以生产实证为准并标注）。
   - Quantumult X：[官方文档仓库 crossutility/Quantumult-X](https://github.com/crossutility/Quantumult-X)（filter 格式规范未在该仓库正文呈现，结论以生产实证为准并标注）。
2. **生产实证**（克隆仓库逐文件核对）：
   - [Repcz/Tool](https://github.com/Repcz/Tool)：五客户端目录 + 每客户端 `.conf`/`Stash.yaml` 模板；Surge/Loon/Shadowrocket/Stash 四个目录的 `YouTube.list`、`Netflix.list` 等**逐字节相同**；Egern 目录为 `*_set` YAML schema。
   - [SukkaW/Surge](https://github.com/SukkaW/Surge)：TypeScript 构建流水线，按客户端族输出 domainset/non_ip/ip 三种格式。
   - [xkww3n/Rules](https://github.com/xkww3n/Rules) 及其 [wiki 配置示例](https://github.com/xkww3n/Rules/wiki)：各客户端引用语法对照。
   - [ClashConnectRules/Egern](https://github.com/ClashConnectRules/Egern)：生产 Egern YAML 配置，实证 `rule_set.match` 直接消费 Surge `.list` / SukkaW `.conf` / Loon `.lsr`。
   - [MetaCubeX/Meta-Docs](https://github.com/MetaCubeX/Meta-Docs)：Clash 族 rule-provider 参考（非 Stash 官方，仅作族参考）。
   - Quantumult X：Repcz `QuantumultX/Rules/*.list` + `QuantumultX.conf`、QuixoticHeart `quantumultx/*.list`、blackmatrix7 `rule/QuantumultX/*` 三家生产文件一致（`HOST*`/`IP-CIDR`/`IP6-CIDR`/`USER-AGENT`，行尾带策略字段）；xkww3n 线上文件用字面占位符 `policy` + 引用行 `force-policy` 覆盖。
3. **社区手册**：[LOWERTOP/Shadowrocket](https://github.com/LOWERTOP/Shadowrocket)（标注"与官方群组同步更新"的手册补完计划；Shadowrocket 无公开官方手册站点，App 内帮助为权威）。

无法由官方规范确认的项目一律标 **Needs Verification**，不凭经验宣布兼容。

## 2. 七客户端审计详情

### Surge（官方手册 + 官方汉化）

- 规则类型：`DOMAIN`、`DOMAIN-SUFFIX`、`DOMAIN-KEYWORD`、`IP-CIDR`、`IP-CIDR6`、`USER-AGENT`、`PROCESS-NAME`、`GEOIP`、`IP-ASN`、`URL-REGEX`、`DEST-PORT` 等。
- 单条格式：域规则两字段 `DOMAIN,value`；IP 规则可选 `no-resolve`：`IP-CIDR,net,no-resolve`。
- **no-resolve**：官方文档明确，防止对域名目标做无效 DNS 解析。
- Rule-Set 文件：官方明确"一行一条规则，**不写策略**"（policy-free classical text）。
- 引用：主配置 `[Rule]` 段 `RULE-SET,<URL>,<policy>[,pre-matching][,extended-matching]`，policy 在引用处。
- 注释：官方 profile format 文档：`#`、`;`、`//` 行注释，`//` 支持行内注释。
- 更新/缓存：App 管理，规则集文件内无 TTL。
- 无损性：Blink 现行 7 种类型全支持（含 USER-AGENT、PROCESS-NAME，Repcz Surge 文件携带二者生产验证）。

### Shadowrocket（LOWERTOP 手册 + 生产实证；无公开官方手册站点）

- 规则类型：`DOMAIN`、`DOMAIN-SUFFIX`、`DOMAIN-KEYWORD`、`DOMAIN-WILDCARD`、`USER-AGENT`、`URL-REGEX`、`IP-CIDR`、`IP-ASN`、`GEOIP`、`RULE-SET`、`DOMAIN-SET`、`SCRIPT`、`DST-PORT`、`AND/OR/NOT`、`PROTOCOL`、`FINAL`。
- **no-resolve**：手册明确（`IP-CIDR,172.16.0.0/12,DIRECT,no-resolve`），域目标跳过 IP 规则、不触发本地 DNS。
- **IP-CIDR6**：手册只描述 `IP-CIDR` 匹配 IPv4/IPv6；Repcz Shadowrocket 目录实际发布 `IP-CIDR6,...no-resolve` 行（Netflix 199 条）→ 生产可用，官方文档级 Needs Verification。
- **PROCESS-NAME**：手册无此类型；手册明确"iOS 没有常规分应用代理，只能域名/IP/UA 分流"；Repcz Shadowrocket 文件丢弃 PROCESS-NAME → 不可无损表达。
- Rule-Set：`RULE-SET,<URL>,<policy>`（Repcz Shadowrocket.conf 生产实证，语法同 Surge）；规则集内容为含规则类型的 classical 行。
- **引用行 no-resolve**：`RULE-SET,<URL>,<policy>,no-resolve` 的第 4 字段被尊重 —— **维护者真机确认（2026-09-12）**。这与上一条的行内 `no-resolve` 是两件事：Blink 的 IP 段视图通过引用行挂载（规则集文件内不写策略也不写选项），所以依赖的是本条而非行内形式。
- 注释：`#`（生产实证）；`;` Needs Verification。
- 更新/缓存：App 内"使用配置/编译配置"或自动更新，文件内无 TTL。存在 Clash 配置导入能力，但原生 RULE-SET 是更自然、维护成本最低的路径（本仓库不依赖 Clash 导入假设）。

### Loon（官方手册仓库）

- 规则类型（官方）：`DOMAIN`、`DOMAIN-SUFFIX`、`DOMAIN-KEYWORD`、`IP-CIDR`、`IP-CIDR6`、`GEOIP`、`IP-ASN`、`USER-AGENT`、`URL-REGEX`、`SRC-PORT`、`DEST-PORT`、`PROTOCOL`、`AND/OR/NOT`、`FINAL`。
- **no-resolve**：官方文档明确（IP 规则可选参数，附专门解释）。
- **USER-AGENT**：官方示例规则文件含 `USER-AGENT,PayPal*` 等行 → 官方支持。
- **PROCESS-NAME**：官方手册全部章节无此类型；Repcz Loon 文件丢弃 → 视为不支持。
- 订阅规则（官方 sub_rule.md）："只要是满足 Loon 类型的规则都可以放入规则集"，引用形式 `URL, POLICY`；主配置 `[Remote Rule]` 段：`URL, policy=X, tag=Y, enabled=true`（Repcz Loon.conf 生产实证）。
- 注释：`#`（生产实证）；`;` Needs Verification。
- 更新/缓存：App 管理，文件内无 TTL。

### Stash（官方 wiki 页面存在；正文不可读，生产实证为主）

- 内核为 Clash Premium 系；配置是 YAML，但 **rule-provider 可直接消费 classical text，不需要 YAML payload**。
- 生产实证（Repcz `Stash.yaml`）：
  ```yaml
  rule-providers:
    YouTube: {behavior: classical, format: text, interval: 86400, url: .../Stash/Rules/YouTube.list}
  rules:
    - RULE-SET,YouTube,Media
  ```
  `format: text` 的 classical payload = policy-free classical 行；`no-resolve`、`IP-CIDR6`、`DOMAIN-KEYWORD`、`PROCESS-NAME` 均保留于 Repcz Stash 文件。
- 变体：xkww3n 使用 Stash 特有 `behavior: domain-text`；mihomo 系另有 `yaml/text/mrs`。**`format: text` 的官方文档级确认 Needs Verification，生产级已证**。
- **引用行 no-resolve**：`rules:` 段的 `- RULE-SET,<name>,<policy>,no-resolve` 尾随选项被尊重 —— **维护者真机确认（2026-09-12）**。同 Shadowrocket：Blink 的 IP 段视图依赖引用行形式，而非 `format: text` payload 内的行内选项。
- **PROCESS-NAME**：✅ Repcz Stash 保留（com.netflix.mediaclient、com.spotify.music）。
- **USER-AGENT**：2026-08 内核源码核对（MetaCubeX/Clash.Meta `rules/parser.go` 与原版 Clash Premium `constant/rule.go`）均**无此规则类型**——classical 加载器对未知类型打 warning 后静默跳过；Repcz 在 Stash 目录丢弃 UA 与此一致。受"四端逐字节相同"约束，Stash 文件保留该行、内核实际跳过 → Needs Verification（真机观察 warning）。
- 注释：`#`（生产实证）；`;` Needs Verification。
- 更新/缓存：`interval: 86400`（provider 级，生产实证）。

### Egern（官方 docs 页面存在；正文不可读，生产实证为主）

- 两条消费路径，均生产实证：
  1. **classical 直接消费**：CCR-Egern 生产配置 `- rule_set: {match: <Surge .list / SukkaW .conf / Loon .lsr URL>, policy: X}`；xkww3n README："纯文本规则集（Surge 标准）适用于 Surge、Stash、Surfboard 和 **Egern**"。policy 在引用处。
  2. **Egern 自有 YAML Rule-Set**（Repcz `Egern/Rules/*.yaml` 生产 schema）：
     ```yaml
     no_resolve: true
     domain_set: [...]
     domain_suffix_set: [...]
     domain_keyword_set: [...]
     ip_cidr_set: [...]
     ip_cidr6_set: [...]
     user_agent_set: ['Argo*']     # USER-AGENT 映射
     url_regex_set: [...]
     ```
- **no-resolve**：rule-set 级 `no_resolve: true`；配置内规则级 `no_resolve: true` 字段（CCR 实证）。全部 IP 规则带 no-resolve 时输出该字段、全不带时省略、混合时显式失败；Blink 的 renderer 三条分支齐备（`engine/tests/test_renderers.py` 有断言）。
- **`url_regex_set`**：Egern schema 有这个 bucket，但 `URL-REGEX` 不在 Blink 的 canonical model（`ALLOWED_RULE_TYPES`）里，任何规则都到不了它，`parity_check` 也不认识该 key，因此 renderer 不保留这个 bucket。若将来把 URL-REGEX 纳入 canonical，renderer 与 parity 两侧必须同时加。
- **PROCESS-NAME**：Repcz Egern 文件丢弃、无对应 key → 不可无损表达（官方文档级 Needs Verification）。
- Egern YAML ≠ Clash YAML：`rules:` 是对象列表（`rule_set` / `domain` / `domain_suffix` / `domain_keyword` / `geoip` / `url_regex` / `default`），与 Clash 完全不同。另支持 `dns.forward` 的 `proxy_rule_set` 做域名级 DNS 分流。
- 注释：`#`（生产实证）。更新间隔字段：Needs Verification。

### Quantumult X（官方仓库存在；filter 格式规范以生产实证为准）

- 规则文件格式（Repcz / QuixoticHeart / blackmatrix7 三家一致）：
  - `HOST,value,policy` ↔ DOMAIN
  - `HOST-SUFFIX,value,policy` ↔ DOMAIN-SUFFIX
  - `HOST-KEYWORD,value,policy` ↔ DOMAIN-KEYWORD
  - `IP-CIDR,cidr,policy` ↔ IP-CIDR
  - `IP6-CIDR,cidr,policy` ↔ IP-CIDR6（QX 的 IPv6 类型名是 `IP6-CIDR`）
  - `USER-AGENT,value,policy` ↔ USER-AGENT
- **策略字段**：QX 行尾必须有策略字段（三家生产源都带）；但主配置 `force-policy` 会覆盖它。xkww3n 线上文件用字面占位符 `policy` 生产运行 → 本仓库同样用占位符 `policy`，实际策略完全由引用行的 `force-policy` 决定（与"输出规则不带策略名"原则在语义上一致：文件内策略无意义）。
- **no-resolve**：三家生产源全部省略（QX 的 filter 行无生产实证的 no-resolve 槽位）→ 本仓库同样省略并记入文档，不静默发明语法。
- **PROCESS-NAME**：三家生产源全部丢弃 → 不可无损表达，显式丢弃 + 报告。
- 引用（Repcz `QuantumultX.conf` 生产实证）：
  ```
  [filter_remote]
  URL, tag=Name, force-policy=Policy, update-interval=172800, opt-parser=false, enabled=true
  ```
- 注释：`#` 头两行（三家一致）。更新/缓存：`update-interval=172800`（48h，引用行内）。

### Clash（Mihomo 内核，Android 通用；官方文档 + 内核源码 + 生产实证）

- 定位：Android 系通用目标。**target = Mihomo（Clash.Meta）内核**（Clash Meta for Android、FLClash 完整兼容）；CFA（Clash Premium 内核，已停更）为部分兼容 legacy——不支持 `format`/`mrs`/`size-limit` 等 Meta 扩展字段。
- 证据：① 官方 [MetaCubeX/Meta-Docs](https://github.com/MetaCubeX/Meta-Docs)（rule-providers / rules / proxy-groups / proxy-providers / dns 章节）+ ① 内核源码逐行核对（[MetaCubeX/Clash.Meta](https://github.com/MetaCubeX/Clash.Meta) `rules/parser.go`、`rules/provider/classical_strategy.go`；[Kuingsmile/clash-core](https://github.com/Kuingsmile/clash-core) `constant/rule.go`、`constant/provider/interface.go`）；② 生产实证：[Repcz/Tool `mihomo/`](https://github.com/Repcz/Tool)（`mihomo/Rules/*.list` classical 含 PROCESS-NAME、全目录无 USER-AGENT；`mihomo/Client/config.yaml` 完整配置范式）、[Paxxs/clash-skk](https://github.com/Paxxs/clash-skk)（classical txt → mihomo rule-provider 生产流水线）。
- rule-providers schema：`type: http`、`behavior: classical`、**`format: text`（必填：默认是 yaml）**、`url`、`interval`（秒；0/省略 = 仅启动加载一次；生产惯例 86400）、`path`（缺省 = url 的 MD5，可选）、`size-limit`（默认 0 不限）。
- 规则类型（classical payload）：`DOMAIN`、`DOMAIN-SUFFIX`、`DOMAIN-KEYWORD`（keyword 小写归一、大小写不敏感）、`IP-CIDR`、`IP-CIDR6`（等价别名）、`PROCESS-NAME`（Android 匹配包名，官方明文 + `component/process` 源码）、`DST-PORT`、`GEOIP`、`MATCH`；**`USER-AGENT` ❌ 内核无此类型**——classical 内 `USER-AGENT` 行被加载器打 warning 后静默跳过（`classical_strategy.go` `Insert()` 不 append、不 count）。
- **Blink 7 种 canonical 类型：6/7 无损，USER-AGENT 为唯一降级项**（受影响 4 条：Netflix / ParamountPlus / PayPal / Spotify 各 1）→ 独立 `Clash/` 目录**显式丢弃并计数**（与 Egern/QX 对 PROCESS-NAME 的先例一致；2026-08 定稿）。
- 引用：`rules:` 段 `- RULE-SET,<name>,<policy>`（支持尾随 `no-resolve`），与内联规则自上而下混排；`MATCH` 为 FINAL 等价尾规则。
- proxy-groups：`select` / `url-test` 原生（`interval`/`tolerance`/`lazy`）；`filter` 正则 + `include-all` 官方支持；**select 组的 `proxies` 数组不引用 provider 名**（订阅池由地区 filter 组覆盖，与 Loon 渲染器同构处理）。
- 主配置：YAML；`mixed-port` / `mode` / `log-level` / `unified-delay` / `keep-alive-interval`（移动端省电，官方建议 15）/ `dns.enhanced-mode: fake-ip`（Android 推荐，默认 redir-host）。
- 注释：classical 文本只认 `#` / `//` 行首（不认 `;`）——Blink classical 用 `#` 头，安全。
- 输出架构决策：`Clash/<App>.list` = classical body 去掉 USER-AGENT 行（其余 6 类逐行同 Surge）；渲染器 = classical 加 per-target 丢弃集；Surge 字节不变（backward compat 门禁不变）。

## 3. Client Capability Matrix

| Rule Type | Surge | Shadowrocket | Loon | Stash | Egern | Quantumult X | Clash |
|---|---|---|---|---|---|---|---|
| DOMAIN | ✅ 官方 | ✅ 手册 | ✅ 官方 | ✅ 内核+生产 | ✅ 生产 | ✅ 生产（HOST） | ✅ 官方 |
| DOMAIN-SUFFIX | ✅ 官方 | ✅ 手册 | ✅ 官方 | ✅ 内核+生产 | ✅ 生产 | ✅ 生产（HOST-SUFFIX） | ✅ 官方 |
| DOMAIN-KEYWORD | ✅ 官方 | ✅ 手册 | ✅ 官方 | ✅ 内核+生产 | ✅ 生产 | ✅ 生产（HOST-KEYWORD） | ✅ 官方 |
| IP-CIDR | ✅ 官方 | ✅ 手册 | ✅ 官方 | ✅ 生产 | ✅ 生产 | ✅ 生产 | ✅ 官方 |
| IP-CIDR6 | ✅ 官方 | ⚠️ 生产可用 / 官方 Needs Verification | ✅ 官方 | ✅ 生产 | ✅ 生产（ip_cidr6_set） | ✅ 生产（IP6-CIDR） | ✅ 官方 |
| USER-AGENT | ✅ 官方 | ✅ 手册 | ✅ 官方示例 | ❌ 内核无此类型（行被跳过）/ 文件保留（四端字节一致） | ✅ 生产（user_agent_set）；classical 内 Needs Verification | ✅ 生产 | ❌ 无此类型（内核源码，显式丢弃） |
| PROCESS-NAME | ✅ 官方 | ❌ 无此类型 | ❌ 官方无 | ✅ 生产保留 | ❌ 无对应 key | ❌ 三家生产源全部丢弃 | ✅ 官方 + 生产保留（Android 匹配包名） |
| no-resolve 语义 | ✅ 官方 | ✅ 手册 | ✅ 官方 | ✅ 生产 | ✅ 生产 | ⚠️ 生产源全部省略 / Needs Verification | ✅ 官方 |
| 注释 `#` | ✅ | ✅ 生产 | ✅ 生产 | ✅ 生产 | ✅ 生产 | ✅ 生产 | ✅ 生产 |
| 注释 `;` / `//` | ✅ 官方 | Needs Verification | Needs Verification | Needs Verification | Needs Verification | Needs Verification | Needs Verification |

## 4. Remote Rule-Set Compatibility Matrix

| | Surge | Shadowrocket | Loon | Stash | Egern | Quantumult X | Clash |
|---|---|---|---|---|---|---|---|
| 引用指令 | `RULE-SET,URL,POLICY` | `RULE-SET,URL,POLICY` | `[Remote Rule]` 段 `URL, policy=P, tag=T, enabled=true` | `rule-providers`（name/behavior/format/url/interval）+ `RULE-SET,name,POLICY` | `rule_set: {match: URL, policy: P}` | `[filter_remote]` 段 `URL, tag=T, force-policy=P, update-interval=172800, opt-parser=false, enabled=true` | `rule-providers`（type/behavior/format/url/interval）+ `RULE-SET,name,POLICY` |
| Policy 位置 | 引用处 | 引用处 | 引用处 | 引用处 | 引用处 | 引用处（force-policy 覆盖行尾占位符） | 引用处 |
| 远程文件带 policy？ | 否 | 否 | 否 | 否（text classical） | 否 | 行尾必有字段（占位符 `policy`，被 force-policy 覆盖） | 否（text classical） |
| 独立 classical 文件 | ✅ | ✅ | ✅ | ✅（format: text） | ✅ | ❌ 需自有 HOST* filter 格式 | ✅（format: text，独立 Clash 目录去 UA） |
| 需要 YAML wrapper/payload | ❌ | ❌ | ❌ | ❌（可选 yaml/mrs 优化） | ❌（可选自有 YAML schema） | ❌ | ❌ |
| 更新/缓存 | App 管理 | App 管理 | App 管理 | `interval: 86400` | App 管理（字段 Needs Verification） | `update-interval=172800` | `interval: 86400` |
| 主配置格式 | INI | INI | INI | YAML（Clash 系） | YAML（自有 schema） | INI | YAML（Clash 系） |
| 引用行 no-resolve 槽位 | ⚠️ 官方语法只列了 pre-matching / extended-matching（见 Needs Verification 11） | ✅ 真机 2026-09-12 | ❌ 无槽位（故 ADAPTED） | ✅ 真机 2026-09-12 | n/a（set 级 `no_resolve`） | ❌ 无生产实证槽位 | ✅ 官方（`rules:` 段尾随） |

> §3 的「no-resolve 语义」行记的是**行内**形式（`IP-CIDR,net,no-resolve`）。Blink 的规则集文件是 policy-free 的，选项只能挂在引用处，因此实际依赖的是上表这一行。两者曾被当成同一件事，是 `ENGINEERING_REVIEW_2026-09.md` 中 O1 的成因。

## 5. 兼容性结论（A–E）

- **A. 可共享同一 output**：Surge / Shadowrocket / Loon / Stash 共享**逐字节相同**的 classical `.list`；Clash 为第 5 个 classical 消费端，但内容 = classical 去掉 USER-AGENT（内核无此类型），故**不**共享逐字节文件、独立 `Clash/` 目录输出。
- **B. 引用方式不同、Rule-Set 内容相同**：上述四客户端；Egern 也能直接消费同一 classical 文件（`rule_set.match`）；Clash 经 `rule-providers`（`behavior: classical, format: text`）消费 UA 丢弃后的 classical 变体。
- **C. 真正需要不同 serialization**：**Egern 自有 YAML schema**（可选但采纳）与 **Quantumult X 自有 filter 格式**（必需：QX 不消费 policy-free classical）。共 3 种序列化格式覆盖 7 客户端（Clash 复用 classical 序列化 + per-target 丢弃集）。
- **D. 无法无损表达的 Canonical Type**：对 **Egern ❌、Quantumult X ❌** 只有 **PROCESS-NAME**；对 **Clash ❌** 是 **USER-AGENT**（内核无此类型，classical 加载器静默跳过 → 必须显式丢弃）。Loon 与 Shadowrocket 无 PROCESS-NAME 类型，但 §7 classical 渲染器的逐字节一致性要求保留该行（客户端忽略未知规则类型），不属于序列化降级。QX 另外无法表达 no-resolve 选项（生产源全部省略）。
- **E. 必须 capability fail/downgrade 的项目**：PROCESS-NAME → 对 Egern / Quantumult X **显式降级丢弃**（构建报告计数，绝不 silent）。受影响 App：Netflix（1 条）、Spotify（1 条）、Disney（2 条）、Hulu（1 条）、Twitch（1 条）、HBO（1 条）。USER-AGENT → 对 Clash **显式降级丢弃**（构建报告计数），受影响 App：Netflix（1 条）、ParamountPlus（1 条）、PayPal（1 条）、Spotify（1 条）。Egern 的 `no_resolve: true` 为 set 级：全部 IP 规则带 no-resolve 时输出，全不带时省略（语义等价），**混合时显式构建失败**。QX 的 no-resolve 省略为全类型统一行为，记入本文档而非逐行报告。

## 6. Shared Output Feasibility

**可行且为最优解**。共享 classical 输出 ×4 客户端 + Clash classical 变体（去 USER-AGENT）×1 + Egern YAML ×1 + QX filter ×1，共 **3 种序列化格式覆盖 7 客户端**。Stash 与 Clash 的关键疑问已有答案：classical text 直接消费（`format: text`），**不需要为它们制造 YAML Rule-Set**；Clash 唯一差异是内核无 USER-AGENT → 独立目录显式丢弃并计数。

## 7. Renderer Architecture

**3 个 Renderer，按真正不同的 serialization format 划分，不按客户端划分**：

| Renderer | 输出 | 目标客户端 | 规则类型处理 |
|---|---|---|---|
| `classical` | policy-free classical text（与现行 `SurgeRule.render()` 字节一致，含两行 `#` 头） | Surge / Shadowrocket / Loon / Stash | 7 种全保留（Stash 文件保留 UA 行，内核跳过 → Needs Verification） |
| `classical-clash` | classical 变体（去 USER-AGENT，其余 6 类逐行同 Surge） | Clash | 6 类保留；USER-AGENT → 显式丢弃 + 报告计数 |
| `egern-yaml` | Egern `*_set` schema | Egern | 域名类 → 对应 set；IP → `ip_cidr(_6)_set` + `no_resolve`；USER-AGENT → `user_agent_set`；PROCESS-NAME → 显式丢弃 + 报告 |
| `quantumultx` | QX filter 行（行尾占位符 `policy`） | Quantumult X | DOMAIN→`HOST`、SUFFIX→`HOST-SUFFIX`、KEYWORD→`HOST-KEYWORD`、IP-CIDR6→`IP6-CIDR`、UA→`USER-AGENT`；no-resolve 省略（文档化）；PROCESS-NAME → 显式丢弃 + 报告 |

Canonical Model 复用现有 policy-free `Rule`，`render()` 从模型移出到 Renderer。Surge 输出 = classical renderer 的一个 target，**字节不变**。

## 8. Output Architecture

```
Surge/<App>.list         # 保持现有路径与字节（backward compat）
Loon/<App>.list          # 与 Surge 逐字节相同
Shadowrocket/<App>.list  # 与 Surge 逐字节相同
Stash/<App>.list         # 与 Surge 逐字节相同
Clash/<App>.list        # classical 去 USER-AGENT（其余逐行同 Surge；UA 丢弃计数）
Egern/<App>.yaml         # Egern schema
QuantumultX/<App>.list   # QX filter 行（行尾占位符 policy，force-policy 覆盖）
```

- 采纳 Repcz/Tool 生态惯例：每客户端独立目录，各客户端用户直接取本客户端目录 URL；git 对相同内容只存一份 blob，仓库体积几乎不增。
- 采纳 SukkaW/Surge 思想：内容（canonical）与每客户端序列化严格分离；README 提供每客户端引用片段。SukkaW 的 domainset/non_ip/ip 拆分与 mihomo `domain/ipcidr` 行为优化对当前规模（≤1158 条/App）无必要，列为未来可选优化。

## 9. Surge Backward Compatibility Plan

1. `Surge/<App>.list` 路径与字节**保持完全不变**：`RULE-SET,https://raw.githubusercontent.com/byyoshen/Blink/main/Surge/<App>.list,<策略>` 持续有效；jsDelivr 镜像说明不变。
2. 重构验收门禁：重构建后 `git diff Surge/` 必须为空（golden-byte 检查）。
3. Surge 路径从不移动 → 无需 alias / 重复发布路径 / staged migration。

## 10. Needs Verification 汇总

1. Stash `format: text` 的官方文档正文（页面存在但本环境不可读）——生产实证充分，风险低。
2. Shadowrocket `IP-CIDR6` 官方文档级确认（生产实证可用）。
3. Stash 的 `USER-AGENT` 行：2026-08 内核源码确认 Clash 族无此类型（classical 内被 warning 后跳过）；受四端逐字节一致约束保留 + 真机观察 warning。
4. Egern 官方文档正文（schema 与 `rule_set` 消费均为生产实证）。
5. QX 官方 filter 格式规范正文（官方仓库未呈现；三家生产源一致，风险低）。
6. QX 行尾策略字段是否可省略、no-resolve 是否有可用槽位——生产源全部带字段/省略 no-resolve，本仓库随生产惯例并文档化。
7. `;` 注释在非 Surge 客户端的支持（本仓库只依赖 `#`，风险可规避）。
8. CFA（Clash Premium 内核）对 mihomo `format` / `mrs` / `size-limit` 等 Meta 扩展字段的行为（忽略 vs 报错）——本仓库 target 为 mihomo 内核，CFA 标注 partial / legacy。
9. Clash 端 `keep-alive-interval` / `unified-delay` 等 Meta 扩展字段在 CMFA / FLClash 的实际表现（官方文档支持，真机验证）。
11. **Surge 引用行的 `no-resolve` 槽位**：§2 记录的官方语法是 `RULE-SET,<URL>,<policy>[,pre-matching][,extended-matching]`，**未列出 `no-resolve`**；而 `build_profile.py` 的 `IP_NO_RESOLVE_CLIENTS` 包含 surge。行内 `no-resolve` 有官方依据，引用行第 4 字段是否同样生效尚无本仓库证据。若不生效，后果是 Surge 的 IP 段静默丢失 no-resolve（即 F1 要修的同一个问题）。需真机或官方文档确认。
10. `keep-alive-interval: 15`（移动端省电建议值）与 `dns.enhanced-mode: fake-ip` 在真机上的功耗与 DNS 表现（官方建议，真机验证）。

## 11. 测试策略（实现阶段）

- **A · Smoke**：OKX（v2fly 转换路径）→ canonical → classical ×4 + Egern YAML + QX filter，人工核对结构。
- **B · YouTube 跨端 E2E**：当前主源 Repcz 14 条不变；七端最小引用示例内置 README（Clash 示例含 UA 丢弃说明）；真机验证首页/搜索/播放/Shorts/图床/CDN/评论/API，观察落 Final、CDN 漏网与七端一致性。
- **C · Complex Semantics**：GitHub（include allow/deny + attributes + exclude + provenance + dedup + nested source）跑全管线七端输出一致性。
- 核心代码禁止 OKX/YouTube/GitHub 业务特例。

## 12. 后续阶段

多客户端输出落地后，重构更新 `engine/portal/` 网页：卡片增加客户端切换/标签页，为每客户端提供对应复制接入行（Surge/Shadowrocket `RULE-SET,URL,POLICY`；Loon `[Remote Rule]` 行；Stash `rule-providers`+`RULE-SET` YAML 片段；Egern `rule_set` YAML 片段 + Egern YAML 文件链接；Quantumult X `[filter_remote]` 行）。

> ✅ 已完成（commit `77ebe22`，QX 于六客户端扩展时加入）：portal 规则集与接入区均带客户端切换与官方 App 图标，`gen_portal_stats.py` 输出每 App 的 `clients` 统计（Egern / Quantumult X 含显式 dropped 计数）。

- 2026-08：第 7 客户端 **Clash（Mihomo 内核 / Android 通用）**审计落地（见 §2.8，内核源码级证据）；`Clash/` 目录（去 USER-AGENT 显式丢弃）与 portal / Profiles / 文档同步扩展中。
- 2026-08-21+：**语义多视图落地**（SukkaW 式 domainset / non_ip / ip 拆分，见 `build.py` 的 `semantic_views` / `phase_of` 与 `engine/scripts/validate_views.py` 门禁）：每个 App 按语义派生出 `-domainset.conf`（纯域名，Surge/Shadowrocket 域名清单、Stash/Clash behavior:domain）/ `-nonip.conf`（含 keyword/UA/PROCESS，classical）/ `-ip.conf`（IP 段，classical/QX filter）七端视图，IP 段恒置于域名段之后；主输出 `.list`/`.yaml` 与各客户端格式事实保持本文件所述不变。
