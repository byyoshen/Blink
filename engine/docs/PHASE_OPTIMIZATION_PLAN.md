# Blink 配置文件层优化 · 执行蓝图

> 状态：**已执行（2026-08-22 全部落地并提交，见第九节）**。本文保留为配置文件层的设计蓝图与决策依据。
> 以遵循 SukkaW 技术思想优化后的 Surge 完整配置为事实基准，结合 SukkaW/Surge 仓库一手源码
> （`Build/lib/rules/base.ts`、`ruleset.ts`、`writing-strategy/{surge,clash}.ts`、`README.md`）提炼的技术思想。
> 规则层（Rule Engine）的 `matching_phase` / 多 view 优化见 `engine/STATUS.md`，**不在本次范围**（单独切片推进）。

## 一、三条已确认原则

1. **边界**：公开 Profile 只含单一订阅池 `Sub`（占位 URL `https://YOUR-SUBSCRIPTION-URL`）；
   双订阅池、个人专属分组与自用域名（自用 Emby / 工具站 / 银行与运营商 App 域名等）
   **不进意图与公开产物**（未在仓库中列具体域名）。
2. **能力矩阵**：Surge 强绑定能力跨端一律 `FULL / ADAPTED(注释标注) / UNSUPPORTED(注释标注)`，禁止静默省略或伪造。
3. **普适化**：公开模板的**策略组 + App 规则只保留 8 个**，其余交由用户自行扩展，并在生成文件头部/README 提示。

## 二、SukkaW 技术思想（SukkaW/Surge 源码证据）

1. **三类规则集 = 三种 DNS 触发行为**：`domainset`（`DOMAIN-SET`，纯域名，不触发 DNS）、`non_ip`（classical `RULE-SET`，
   不触发 DNS）、`ip`（classical `RULE-SET` 或 `ipcidr`，触发 DNS）。
2. **domain-first / IP-last 是强制不变式**：所有 `domainset`/`non_ip` 与自加 `DOMAIN`/`DOMAIN-SUFFIX`/`DOMAIN-KEYWORD`
   必须放在所有 `ip` 规则组与自加 `IP-CIDR`/`IP-CIDR6`/`IP-ASN`/`GEOIP` 之前，**没有例外**；违反即失去 DNS 污染保护。
3. **canonical 数据 → 多客户端 writing strategy**：`FileOutput`（type 桶）→ `SurgeRuleSet`/`ClashClassicRuleSet`/
   `ClashDomainSet`/`ClashIPSet`/`ClashPremium`/`Surfboard`/`sing-box`。同一份数据派生所有客户端，format 只由 strategy 决定。
4. **按类型桶分类存储**：`domainTrie`（`HostnameSmolTrie`）/`keyword`/`wildcard`/`userAgent`/`processName`/`processPath`/
   `urlRegex`/`ipcidr`/`ipcidrNoResolve`/`ipcidr6`/`ipasn`/`geoip`/`destPort`/`protocol`/`otherRules`。
5. **provenance 内嵌**：每个输出 description 区记录 `This file contains data from: ...`。
6. **性能与范围敏感**：`OUTPUT_WORKER_THRESHOLD=20000`；reject 三档 domainset（12万/9万/13万）仅建议 Surge for Mac，
   移动端用 ADGuard；`URL-REGEX` 需 MITM、不推荐。
7. **运行层能力与规则源分家**：`always-real-ip`/`always-raw-tcp-hosts`/`hijack-dns`/`proxy-test-udp`/`sgmodule(MITM)` 在 Profile/模块层；
   `PROTOCOL,MTProto` 是 Profile 传输引用，规则源只出 domain/ip/ASN。`ClashClassicRuleSet.writeUserAgents=noop`（Clash 无 UA）。

## 三、公开模板策略组结构（定稿）

```
Sub                      # 订阅池（占位 URL）
# 出口骨架（保留地区组 + Auto，非场景组；视作核心分流基础设施）
HK/TW/JP/US/SG          select + policy-regex-filter（从 Sub 筛节点）
Auto                    url-test(HK,TW,JP,US,SG, interval=600, tolerance=80, hidden)
Proxy = select, HK,TW,JP,US,SG, Final
Final = select, HK,TW,JP,US,SG, Auto, Sub, DIRECT
# App 场景组（只 6 个；成员统一 select, Proxy, Final, DIRECT）
Telegram / X / Youtube / Instagram / Google / Github
```
其余场景组与 App 路由（AI / Daily / Finance / APTV / Emby / AppleMusic / Steam / Netflix / TikTok / Spotify /
WhatsApp / LINE / OKX / PayPal / SafePal / ZABank / Disney / HBO / Hulu / PrimeVideo / Twitch / ParamountPlus /
Facebook / NBA / Suno）**移出公开模板**，生成文件注释提示「按需自行扩展」。

## 四、General 技术基线（SukkaW 思想）

| 类别 | 项 | 跨端呈现 |
|---|---|---|
| 通用基线 | `loglevel=notify`、`dns-server`、`encrypted-dns-server`、`hijack-dns=*:53`、`ipv6=false`、`udp-policy-not-supported-behaviour=REJECT`、`test-timeout=5`、`show-error-page-for-reject=true` | 各端映射到自有字段（Loon/Stash/mihomo 的 `dns`/`fake-ip`/`ip-mode` 等） |
| Surge 强绑定 | `skip-proxy`、`always-real-ip`、`always-raw-tcp-hosts`、`proxy-test-udp`、`http-api*`、`internet-test-url`、`proxy-test-url` | 非 Surge 端 `ADAPTED`（注释「请在 App 内配置」）或 `UNSUPPORTED` |

## 五、Rule 引用结构（domain-first / IP-last）

```
Reject:   reject-drop.conf → REJECT-DROP, pre-matching
          domainset/reject.conf → REJECT, extended-matching
          non_ip/reject.conf → REJECT, extended-matching
          Tracking.list → REJECT, extended-matching
Infra:    DEST-PORT 123 → DIRECT；non_ip/lan.conf → DIRECT
Apple/CN: non_ip/apple_cn.conf、domainset/apple_cdn.conf → DIRECT
Business: 6 App RULE-SET（Telegram/X/Youtube/Instagram/Google/Github）+ extended-matching
Domestic: non_ip/domestic.conf → DIRECT
CDN:      non_ip/cdn.conf + domainset/cdn.conf → Proxy
IP:       ip/telegram.conf、ip/domestic.conf、ip/china_ip.conf → no-resolve
Final:    FINAL → Final, dns-failed
```
> Blink 的 6 个 App 规则引用：Surge/Shadowrocket/Loon/Stash/Egern 走 `Surge/<App>.list`，
> mihomo 走 `mihomo/<App>.list`（已去 USER-AGENT）。跨端对 `extended-matching` 仅 Surge FULL，其余 UNSUPPORTED（注释）。

## 六、能力矩阵框架（实施时逐项定）

| 能力 | Surge | Shadowrocket | Loon | Stash | mihomo | Egern | Quantumult X |
|---|---|---|---|---|---|---|---|
| `extended-matching` | FULL | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `pre-matching` | FULL | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `no-resolve` | FULL | FULL | ADAPTED（仅行内） | FULL | FULL | set 级 | UNSUPPORTED |
| `REJECT-DROP` | FULL | FULL | FULL | FULL | FULL | ADAPTED→REJECT | ADAPTED→reject |

> 以 `engine/docs/MULTI_CLIENT_AUDIT.md` 为最终格式事实；冲突先改本文再改代码。各端字段无生产实证一律 UNSUPPORTED。

> `no-resolve` 的落点分两层，必须同时看：规则集**行内**选项，和**引用行**选项。
> Surge / Shadowrocket / Stash / mihomo 的引用行都有槽位（`build_profile.IP_NO_RESOLVE_CLIENTS`
> 是这份判断的唯一代码实现）；Loon 的 `[Remote Rule]` 引用行没有槽位，只能依赖规则集行内选项，
> 所以对行内不带 `no-resolve` 的外部 IP 规则集（如 `skk List/ip/china_ip.conf`，3900 行全不带）
> 是 ADAPTED 而非 FULL，已在 `templates/loon.conf` 头部显式标注。Blink 自产的 `-ip.conf`
> 行内全部带 `no-resolve`，因此 App 的 IP 段在七端都受保护。

## 七、分阶段实施细则（横向切片：一次一功能 × 七端，逐切评审）

- **切片 0 · 意图定稿**：重写 `intent.yaml`（subscription / policy_groups=8+骨架 / apps=6 / infrastructure=ordering / 能力声明）。
- **切片 1 · General**：七端模板 General 骨架 + build_profile 通用字段渲染 + `build_profile.py --write` 重建 `Profiles/`。
- **切片 2 · Proxy Group**：地区组 + Auto + Proxy + Final + 6 App 组七端渲染。
- **切片 3 · Rule ordering + 能力**：infrastructure 重排序 + `extended/pre/no-resolve/PROTOCOL,MTProto/REJECT-DROP` 各端 FULL/ADAPTED/UNSUPPORTED。
- 每切片跑：单测 + `build_profile.py --write` + `verify_profiles.py` + `build.py --verify-only` + parity/health/overlap/manifest。

## 八、明确不做

- 不改规则产物与公开 URL（`Surge/<App>.list` 逐字节不变）。
- 不改行为、不重写 parser；只扩展 Profile 层。
- 不复刻 SukkaW 的大规模 domainset（引用其 URL）。
- `always-real-ip`/`always-raw-tcp-hosts`/`skip-proxy` 只在 Profile 层，不进规则源。
- 不引入 MTProto secret / `dc-config-url` / 双订阅池 / 个人域名。
- 本次不含 Rule 层 `matching_phase` / 多 view（单独切片）。

## 九、落地记录（2026-08-22）

配置文件层（Profile + Ruleset 语义化）已按上文全部落地并提交：

**① Rule 层 multi-view（matching_phase + 分文件）**
- `build.py`：新增 `PHASE_BY_KIND`（domain/nonip/ip）+ `semantic_views()`，把每 App canonical 拆成
  domainset / nonip / ip 三段（domain-first / IP-last；纯域名 App 不生成空 IP view）。
- `renderers.py`：新增 `render_surge_domainset`、`render_mihomo_domainset`、统一 `render_view`；
  各端 view 文件（`.conf` 后缀，避开 parity 的 `.list`/`.yaml` glob）：Surge/Shadowrocket 域名清单、
  Stash/mihomo `behavior:domain`、Loon/Egern classical、QX `HOST*` filter；均 policy-free。
- 全部 30 App 开启 `views:true`，产出七端 domainset/nonip/ip view 文件（主输出 `.list`/`.yaml` 零改动）。
- `verify_manifest.py`：`views` 字段校验（per-client + 各端目录路径约定）。

**② Profile 层分文件引用**
- `intent.yaml`：6 个路由 App 声明 `views: [...]`（Telegram/X `[domainset,ip]`、YouTube `[nonip]`、
  Instagram/GitHub `[domainset]`、Google `[nonip,ip]`）。
- `build_profile.py`：7 端 App 路由按 app 声明 views 生成分文件引用（domainset→DOMAIN-SET/behavior:domain、
  ip→RULE-SET,no-resolve、nonip→classical）。
- 已移除与各 App ip view 重复的 infra `telegram-ip` 条目。

**③ portal**：`gen_portal_stats.py`/`types.ts`/`data.ts`/`Rulesets.tsx` 展示每 App 的 view 分段、
按 view 生成复制接入，并更新各客户端引导文案（说明域名→IP 拆分）。

**使用**：主输出 `.list`/`.yaml` 与公开 URL 稳定；带 IP 的 App 可改用
`<App>-domainset.conf` / `<App>-nonip.conf` / `<App>-ip.conf` 分文件引用达成 domain-first/IP-last。
