# Blink Source Audits

> 每个 App 的独立 source audit 记录：候选来源、证据、结论与选择理由，按 App 分节集中保存。
> 最终的精简理由同步写入 `engine/sources/apps.yaml` 对应 App 的 `note` 字段；本文件是完整审计档案。

## 审计政策摘要

- 上游优先偏好与选源标准（freshness/completeness/scope/format/maintenance）以 [AGENTS.md](AGENTS.md) 为准，此处不重复。
- Manifest 硬约束：每个 App 恰好 1 个 primary source，最多 1 个 supplemental source；输出规则不带策略名。
- 构建器 v1 格式边界（下文各 App 的“格式风险”据此标注）：
  - `v2fly-domain-list`：`domain`/`full`/`keyword` 映射为 Surge `DOMAIN-SUFFIX`/`DOMAIN`/`DOMAIN-KEYWORD`；regexp 与 `@!` 否定属性直接构建失败；带 `@attribute` 的条目默认被跳过（除非 manifest 显式 include）；`include` 必须在 include_policy 显式 allow/deny，否则构建失败。
  - `surge-rule-set`（严格白名单）：仅接受无策略名的 `DOMAIN`、`DOMAIN-SUFFIX`、`DOMAIN-KEYWORD`、`USER-AGENT`、`PROCESS-NAME`、`IP-CIDR`、`IP-CIDR6`；IP 仅允许额外 `no-resolve`。`IP-ASN`、`URL-REGEX`、带策略名等会导致构建失败。
  - 多客户端输出边界（v1.1，见 `engine/docs/MULTI_CLIENT_AUDIT.md`）：canonical 规则渲染为 classical（Surge / Loon / Shadowrocket / Stash 逐字节相同，7 种类型全保留）、egern-yaml（Egern）与 quantumultx（Quantumult X）；`PROCESS-NAME` 对 Egern / Quantumult X 显式丢弃并计入构建报告；classical 保留该行（Loon / Shadowrocket 无此类型，客户端直接忽略），禁止静默转换。
- `engine/sources/supplement/<App>.list` 仅存放上游未覆盖、且由客户端日志（当前以 Surge 为准）或实际使用确认的缺口。

## 审计状态

| App | 状态 | 结论摘要 |
| --- | --- | --- |
| AI | 已落地 | Repcz `AI.list`（50 条输出；1 条 URL-REGEX 已类型级排除） |
| TikTok | 已落地 | Repcz `TikTok.list`（81 条输出；2 条 IP-ASN 已类型级排除） |
| Spotify | 已落地 | Repcz `Spotify.list`（21 条），零转换风险，无需 supplemental |
| ZABank | 已落地 | supplement-only（`sources: []` + 3 条根域名），上游 5+ 家全部缺失 |
| Steam | 已落地 | Repcz `Steam.list`（20 条核心域名），零转换风险，无需 supplemental |
| APTV | 已落地 | supplement-only 个人维护直播清单（26 条，2026-08-15 迁入；原计划名 Live） |
| Disney | 已落地 | Repcz `Disney.list`（174 条；2 条 PROCESS-NAME 对 Egern/QX 显式丢弃） |
| ParamountPlus | 已落地 | blackmatrix7 `ParamountPlus.list`（10 条，全网唯一专项源） |
| Hulu | 已落地 | blackmatrix7 `Hulu.list`（59 条；v2fly 2022 陈旧，Repcz/SukkaW 无专项） |
| PrimeVideo | 已落地 | Repcz `PrimeVideo.list`（16 条，含 6 条精确 CloudFront 分发域名） |
| HBO | 已落地 | Repcz `HBO.list`（48 条 − 2 条通用 AWS API Gateway 后缀 = 46 条） |
| Twitch | 已落地 | blackmatrix7 `Twitch.list`（22 条：域名+关键字+IP 覆盖） |
| Facebook | 已落地 | Repcz `Facebook.list`（580 条，含防钓鱼拼写变体） |
| Google | 已落地 | Repcz `Google.list`（25 条；KEYWORD google/gmail 覆盖搜索与 Gmail） |
| NBA | 已落地 | supplement-only（2 条根域；无上游，如日后使用暴露缺口按政策补） |
| Suno | 已落地 | supplement-only（2 条根域；无上游，如日后使用暴露缺口按政策补） |

## 早期 12 个 App 的审计结论索引

以下 App 在本档案建立（2026-08-15）之前完成审计与落地，未逐 App 分节；精简理由见 `engine/sources/apps.yaml` 各 App 的 `note`，演进历史见 `STATUS.md`。

| App | Primary | 格式 | 要点 |
| --- | --- | --- | --- |
| OKX | v2fly | v2fly-domain-list | `oklink.com @cn` 未启用；覆盖此前 7 条手工补充域名（okx-dns/dns1/dns2、okx.ac、okx.cab、okx.com.cdn.cloudflare.net、xlayer.tech） |
| WhatsApp | v2fly | v2fly-domain-list | `@ads` graph 条目未启用 |
| LINE | v2fly | v2fly-domain-list | 不引入整个 `naver.jp`；`nhncorp.jp` 仅凭证据处理 |
| GitHub | v2fly | v2fly-domain-list | allow `github-copilot`、deny `npmjs`；不扩大为 Microsoft/Amazon/Azure 公共基础设施 |
| SafePal | v2fly | v2fly-domain-list | 上游已覆盖 `isafepal.com` 与 `safepal.com` |
| PayPal | Repcz | surge-rule-set | 与 blackmatrix7 输出规范化后等价，按作者偏好选 Repcz |
| Netflix | blackmatrix7 | surge-rule-set | 保留 IPv4/IPv6 与 `no-resolve` 语义 |
| YouTube | Repcz | surge-rule-set | 紧凑核心专项范围 |
| X | Repcz | surge-rule-set | 保留 X/Twitter/Grok/媒体与已审计窄范围 IP |
| Instagram | Repcz | surge-rule-set | 排除过宽 `DOMAIN-KEYWORD,instagram` |
| Telegram | SukkaW | surge-rule-set | 仅核心域名（主配置保持 MTProto + Repcz 双列表，含 IP 覆盖）。2026-08 起为 Rule 层 multi-view pilot 增加 supplemental IP 源 `ruleset.skk.moe/List/ip/telegram.conf`（官方 Telegram CIDR 15 条，2026-08-13，AGPL 3.0），使 canonical 兼具 domain 与 IP 两段 |
| Threads | v2fly | v2fly-domain-list | `threads.com`/`threads.net` 窄集合 |

## 各 App 审计记录

### TikTok

审计日期：2026-08-15。以下 URL 与正文均为当日直接抓取验证（Node.js fetch）。

候选来源：

| 候选 | 作者 | URL | 格式 | Surge 原生 | 规模/覆盖 | 维护证据 | 过宽/无关条目 | 格式风险 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Repcz（一梯队） | Repcz | `https://raw.githubusercontent.com/Repcz/Tool/X/Surge/Rules/TikTok.list`（200） | surge-rule-set | 是 | 83 条：DOMAIN 19 / DOMAIN-SUFFIX 55 / DOMAIN-KEYWORD 7 / IP-ASN 2；覆盖 tiktok.com、cdn、musical.ly、byteimg/byte* CDN、ttlive 等 | 仓库每日自动更新，分支 head 2026-08-15（仓库历史重写，无逐文件 commit） | cocacola.co.jp、api.snapkit.com、courses.snapsolve.com（Snap 系）、engagements.appsflyer.com、roovza-*.appsflyersdk.com（AppsFlyer SDK）、capcut.com、musemuse.cn | 尾部 2 条 `IP-ASN,11983/138699,no-resolve` 超出 build.py v1 白名单，当前会构建失败 |
| SukkaW（一梯队） | SukkaW | 无 TikTok 专项（仓库递归树 0 命中 tiktok/bytedance/capcut 等） | — | — | — | — | — | 不存在专项规则，非被降级 |
| blackmatrix7 | blackmatrix7 | `.../rule/Surge/TikTok/TikTok.list`（200） | surge-rule-set | 是 | 33 条 | 最后 commit 2025-12-21；文件头 UPDATED 2025-08-10（约 8 个月陈旧） | marscode.com、trae.ai、trae-api-sg.mchost.guru、byteintlapi.com（字节 AI IDE 工具）、capcut.com、snssdk.com（抖音 SDK）；`DOMAIN-KEYWORD,tiktok` 过宽 | 格式全白名单兼容，但陈旧且范围漂移 |
| v2fly | v2fly | `.../master/data/tiktok`（200） | v2fly-domain-list | 否 | 36 条：25 裸后缀 + 10 `full:` + 1 `@ads` | 最后 commit 2026-08-05（活跃） | `full:roovza-*.appsflyersdk.com`（AppsFlyer SDK） | 全部条目带 `@!cn` 否定属性，v1 对否定属性直接构建失败，不可用 |
| MetaCubeX | MetaCubeX | 无 TikTok 文本产物（树 0 命中） | — | — | — | — | — | 无 |

推荐 primary：**Repcz TikTok.list**。理由：一梯队、Surge 原生、覆盖最完整（83 条含 CDN/关键字/IP）、维护最活跃；唯一障碍是 2 条 IP-ASN，需要一次显式、可审计的清单/构建器决策（见下方“待决策”）。可选 exclude（若希望收紧）：cocacola.co.jp、api.snapkit.com、courses.snapsolve.com、engagements.appsflyer.com、roovza-launches.appsflyersdk.com、capcut.com、musemuse.cn。

supplemental：**不需要**。v2fly 独有的边缘域名（tiktok-minis.com、tiktok-row.net、tiktokeu-cdn.com、ttcdn-us.com 等）按政策等待 Surge 日志确认后再补。

决议（2026-08-15）：build.py 已增加类型级 exclude，manifest 使用 `exclude: ["ip-asn:*"]` 显式丢弃 2 条 IP-ASN；输出 81 条，构建报告 `skipped_excluded: 2`。审计中列出的可选收紧项（cocacola.co.jp、Snap 系、AppsFlyer SDK、capcut.com 等）暂不排除，等待 Surge 日志证据。

### Spotify

审计日期：2026-08-15。以下 URL 与正文均为当日直接抓取验证。

候选来源：

| 候选 | 作者 | URL | 格式 | Surge 原生 | 规模/覆盖 | 维护证据 | 过宽/无关条目 | 格式风险 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Repcz（一梯队） | Repcz | `https://raw.githubusercontent.com/Repcz/Tool/X/Surge/Rules/Spotify.list`（200） | surge-rule-set | 是 | 21 条：SUFFIX 17 + KEYWORD 1（-spotify-com）+ IP-CIDR 1（35.186.224.47/32,no-resolve）+ PROCESS-NAME com.spotify.music + USER-AGENT Spotify* | 仓库每日自动更新（分支 head 2026-08-15）；文件自身最后提交 2026-08-06（仓库历史重写） | 无共享 CDN/广告/第三方；akamaized 均为 spotify 专属（spotify-com.akamaized.net 同时覆盖 audio4-ak/heads-ak 等） | 无：全部在 v1 白名单内，零转换风险 |
| SukkaW（一梯队） | SukkaW | 无独立 Spotify 文件（`Source/non_ip/spotify.conf` 404）；SPOTIFY 常量内嵌于 `Source/stream.ts`（20 条，与 Repcz 内容几乎一致），发布物为合并 `ruleset.skk.moe/List/non_ip/stream.conf`（409 行多服务混排） | TS 源码 + 合并 conf | 语法原生但非独立列表 | 20 条 | stream.ts 最后提交 2025-11-13（约 9 个月） | 同 Repcz | 需从 TS 抽取或从合并 stream.conf 拆分，无直接可用的窄范围产物 |
| v2fly | v2fly | `.../master/data/spotify`（200） | v2fly-domain-list | 否 | 25 条：17 裸后缀 + 8 `full:` + 3 `@ads` | 最后 commit 2026-06-23 | 第三方 `full:cdn-spotify-experiments.conductrics.com` 会直接混入（需 exclude）；3 条 @ads 追踪域默认被跳过 | 可转换，无 regexp/include/@! 否定 |
| blackmatrix7 | blackmatrix7 | `.../rule/Surge/Spotify/Spotify.list`（200） | surge-rule-set | 是 | 31 条：DOMAIN 6 + KEYWORD 1（spotify，偏宽）+ SUFFIX 20 + IP-CIDR 2 + PROCESS-NAME 1 + USER-AGENT 1 | 文件头 UPDATED 2025-06-06；最后 commit 2025-06-17（约 14 个月陈旧） | 第三方 conductrics.com；`DOMAIN-KEYWORD,spotify` 过宽 | 格式干净但过时 |
| MetaCubeX | MetaCubeX | 无 Surge 文本 Spotify 产物（geosite 数据源自 v2fly，内容等价） | 二进制 dat | 否 | — | — | — | 不适合直接作源 |

推荐 primary：**Repcz Spotify.list**。理由：一梯队、可直接消费的独立 Surge 原生文件、覆盖核心域名 + 音频 CDN + IP + 进程 + UA；与 SukkaW 内容规范化后等价时，作者优先偏好作为 tie-breaker，且 Repcz 更活跃、产物可直接使用。

supplemental：**不需要**。其他源中非冗余条目（spotify.map.fastly.net、spotify.map.fastlylb.net、spotify.com.edgesuite.net、spotify.link）均为边缘 CDN/短链，按“仅日志确认缺口才补”原则暂不预补；conductrics.com 属第三方，明确不纳入。

无需任何构建器改动，可直接按现有 manifest 结构新增。

### AI（聚合式 Rule-Set）

审计日期：2026-08-15。目标：单一聚合 AI Rule-Set，覆盖主流 AI 服务（ChatGPT/OpenAI、Claude、Gemini、Perplexity、Poe、Grok、Copilot 等）。以下 URL 与正文均为当日直接抓取验证。

候选来源：

| 候选 | 作者 | URL | 格式 | Surge 原生 | 规模/覆盖 | 维护证据 | 过宽/无关条目 | 格式风险 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SukkaW（一梯队） | SukkaW | `https://raw.githubusercontent.com/SukkaW/Surge/master/Source/non_ip/ai.conf`（200） | surge-rule-set（conf 语法） | 是 | 51 条有效行（含 1 条 URL-REGEX）：OpenAI/ChatGPT（openai/oaistatic/sora/chatgpt/chat.com/ai.com + KEYWORD openai）、Claude（anthropic/claude.ai/claude.com）、Perplexity、Google AI（bard/gemini/aisandbox/deepmind/generativelanguage/aistudio/makersuite/notebooklm/jules/antigravity/aida/generativeai 等）、Poe、Meta AI、Cloudflare AI Gateway、Dify、Jasper/Clipdrop、OpenArt、Copilot（api.github.com）、Grok（grok.com/x.ai）、Groq、JetBrains AI、OpenRouter | 最后 commit 2026-08-06（活跃，PR 溯源完整） | 无共享 CDN；均为各服务自有域 | 1 条 `URL-REGEX,https://www\.google\.com/.*continue=https://gemini\.google\.com.+`（修复 Gemini 429 sorry 跳转，需 MitM www.google.com）超出 v1 白名单 |
| Repcz（一梯队） | Repcz | `https://raw.githubusercontent.com/Repcz/Tool/X/Surge/Rules/AI.list`（200） | surge-rule-set | 是 | 51 条；内容与 SukkaW ai.conf 几乎逐条一致（明显派生自 SukkaW），额外多 `DOMAIN,file.oaiusercontent.com`（OpenAI 文件 CDN） | 仓库每日自动更新（分支 head 2026-08-15） | 同 SukkaW | 同 SukkaW：1 条相同 URL-REGEX |
| v2fly | v2fly | `.../master/data/category-ai-!cn`（200） | v2fly-domain-list | 否 | 约 30 个 include（anthropic/cursor/github-copilot/huggingface/manus/openai/perplexity/poe/xai 等）+ 数十个杂项 AI 工具域（midjourney/mistral/ollama/lmstudio/crewai/devin 等） | 最后 commit 2026-08-04 | 范围远超“主流 AI 服务”需求，含大量小众工具 | include 全部需显式 allow/deny（管理成本高）；且包含 bytedance-ai-!cn 等，范围失控 |
| blackmatrix7 | blackmatrix7 | 无聚合 AI.list（404）；分服务列表：OpenAI 35 / Copilot 51 / Gemini 13 / Claude 3 | surge-rule-set | 是 | 覆盖分散 | 文件头 UPDATED 2025-06-06（陈旧） | 大量第三方基础设施（statsig/auth0/intercom/sentry/stripe/launchdarkly/algolia 等）、telemetry 域；OpenAI/Copilot 各含 IP-ASN | 聚合需拼接 4+ 源，超出“1 primary + ≤1 supplemental”约束 |
| MetaCubeX | MetaCubeX | 无直接可用的 Surge 文本聚合产物 | — | — | — | — | — | 不适合直接作源 |

推荐 primary：**Repcz AI.list**（备选 SukkaW ai.conf）。理由：两个一梯队候选规范化后基本等价（Repcz = SukkaW + `file.oaiusercontent.com`）；按“候选规范化后等价时作者优先偏好作 tie-breaker”选 Repcz；若更看重原版与 PR 溯源，可改选 SukkaW ai.conf（同样活跃，2026-08-06）。两者都必须显式处理 1 条 URL-REGEX（见“待决策”）。

supplemental：**不需要**。

其他注意事项：
- **DeepSeek 未覆盖**：Repcz/SukkaW 聚合均不含 deepseek.com（v2fly `data/deepseek` 仅 1 行 `deepseek.com`；blackmatrix7 无）。推测原因是 DeepSeek 为国内服务、通常直连；是否纳入 AI 聚合另行决策（若纳入，在 primary 之外需另做决策——supplement 按政策要求日志确认缺口）。
- **与既有输出的重叠**：AI 聚合含 grok.com/x.ai（与 X.list 的 Grok 覆盖重叠）与 api.github.com（与 GitHub.list 的 copilot 覆盖重叠）。Surge 中不同 RULE-SET 按顺序命中，重叠无害；仅在此记录。
- 决议（2026-08-15）：build.py 已增加类型级 exclude，manifest 使用 `exclude: ["url-regex:*"]` 显式丢弃 1 条 URL-REGEX；输出 50 条，`skipped_excluded: 1`。DeepSeek 未纳入（国内直连默认；须日志确认缺口后才可进 supplement）。

### ZABank

审计日期：2026-08-15。以下 URL 与状态码均为当日直接抓取验证（Node.js fetch）。

候选来源：**全部缺失**。

| 作者 | 验证结果 |
| --- | --- |
| Repcz | X/Surge/Rules 目录 75 个 .list 无 ZABank；`ZABank.list`、`ZA-Bank.list`、`ZABANK.list`、`za-bank.list`、`Bank.list`、`Finance.list` 全部 404 |
| SukkaW | `Source/non_ip` 仅 29 个文件，无 za 相关；`hk.conf` 404 |
| v2fly | `data/zabank` 404、`data/zainvest` 404；全量树 1536 个 `data/*` 无 zabank/zainvest/za.group；银行类目仅 `category-bank-cn/ir/jp/mm/ru`（无 HK） |
| blackmatrix7 | `rule/Surge` 670 项无 ZABank；`ZABank/ZABank.list` 404、`ZA/ZA.list` 404 |
| MetaCubeX | 规则以二进制 Releases 分发，仓库树内无 za/bank/hk 文本规则 |
| xkww3n/Rules（成熟作者） | 74 项无 za |

9 个候选域名对照：全部未覆盖，且全部是三个根域名的子域名：

- `za.group`：wbs、i18n、offlineapp、bankappgw、aim-abtesting-sdk
- `zainvest.group`：bank-stock、bank-sbsmarket
- `zajourney.com`：appmon-prd、integrate-appgw

推荐方案：无成熟上游可作 primary。以 3 条根域名 `DOMAIN-SUFFIX,za.group` / `DOMAIN-SUFFIX,zainvest.group` / `DOMAIN-SUFFIX,zajourney.com` 建立最小规则集，即可覆盖全部 9 个候选域名；纯 DOMAIN-SUFFIX，零转换风险，兼容 build.py 两种格式。

决议（2026-08-15）：采用方案 (a) —— build.py 允许 `sources: []`（supplement-only），manifest 已落地：`engine/sources/supplement/ZABank.list` 写入三条根域名，输出 3 条规则。9 个候选域名来自实际使用记录（此前交接文档中的候选清单）；如与实测不符可随时调整。

### Steam

审计日期：2026-08-15。触发原因：维护者主配置仍引用 blackmatrix7 Steam，是当时唯一未被 Blink 覆盖的非国内 App。以下 URL 与正文均为当日直接抓取验证（Node.js fetch；GitHub API 本轮被限流，维护时间沿用同日对同仓库的实测）。

| 候选 | 作者 | URL | 格式 | Surge 原生 | 规模/覆盖 | 维护证据 | 过宽/无关条目 | 格式风险 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Repcz（一梯队） | Repcz | `https://raw.githubusercontent.com/Repcz/Tool/X/Surge/Rules/Steam.list`（200） | surge-rule-set | 是 | 20 条 DOMAIN-SUFFIX：核心 Steam（store/community/chat/content/steamdeck/steamstatic 等）+ fanatical、humblebundle（游戏商店） | 仓库每日自动更新（2026-08-15 分支 head，同日实测） | 无 CDN 专属/中国区主机；fanatical/humblebundle 属游戏生态，可接受 | 无：全白名单兼容，零转换风险 |
| SukkaW（一梯队） | SukkaW | 无 Steam 专项（`Source/non_ip/steam.conf` 404；当日树查询被 API 限流，结合前次全树审计无 steam 相关文件） | — | — | — | — | — | 无专项规则 |
| v2fly | v2fly | `.../master/data/steam`（200） | v2fly-domain-list | 否 | 非 @cn 有效条目约 35 条：17 裸后缀 + 12 条 akamai `full:` + 网宿/highwinds/地区 CDN + dota2/valve.net；另有约 14 条 `@cn`（完美/蒸汽中国 CDN，默认跳过） | 活跃（2026-08 系列提交，同日实测） | 地区性 CDN（internode NZ/orcon/webra RU/comcast edgecast/hwcdn）价值存疑，偏宽 | 无 regexp/include/否定属性；可转换但需甄别 CDN 条目 |
| blackmatrix7 | blackmatrix7 | `.../rule/Surge/Steam/Steam.list`（200） | surge-rule-set | 是 | 54 条：51 SUFFIX + 3 KEYWORD | 文件头 UPDATED 2025-06-06（约 14 个月陈旧） | **含盗版站 `steamunlocked.net`**；3 条宽关键字（steambroadcast/steamstore/steamuserimages）；大量中国区 CDN 主机 | 格式干净但陈旧且范围不干净 |
| MetaCubeX | MetaCubeX | 无文本 Steam 产物（`meta/Steam.list` 404） | — | — | — | — | — | 不适合直接作源 |

推荐 primary：**Repcz Steam.list**。理由：一梯队、Surge 原生、20 条核心域名零转换风险、每日更新；v2fly 偏宽（地区 CDN），blackmatrix7 陈旧且含无关域名。无需 supplemental、无需任何构建器改动。

### APTV（个人维护直播清单）

审计日期：2026-08-15。原计划名“Live”，因实际通过 APTV 前端 App 观看直播而命名 APTV。

- **来源**：此前私有保存的 `Surge/Rules/LiveStreaming.list`（garyshare 直播源，原文件版本 2026-02-22），26 条（17 DOMAIN + 4 DOMAIN-SUFFIX + 5 IP-CIDR,no-resolve），全部 policy-free 且在 build.py v1 白名单内，无需转换。
- **落地方式**：supplement-only（`sources: []` + `engine/sources/supplement/APTV.list`），与 ZABank 同一模式；supplement 文件头部注明个人维护，manifest note 记录迁移来源与免责说明。
- **安全**：内容仅含域名与 IP，不含订阅 URL 或 token；他人复用本仓库时请自行评估是否移除本 App。
- **主配置**：已改为引用 `Surge/APTV.list`，策略仍由主配置指定。

## 与维护者 Surge 主配置的对照（2026-08-15，已脱敏）

对维护者 iOS 端主配置 `[Rule]` 段与仓库输出做了一次完整对照。本记录已脱敏，不含主配置中的个人域名与订阅相关条目。

- **ZA Bank**：主配置有 9 条手工 `DOMAIN`（za.group / zainvest.group / zajourney.com 子域）。Blink `ZABank.list` 的三条根域名完整覆盖，可删除 9 条手工行。
- **SafePal**：主配置只有 `isafepal.com`；Blink `SafePal.list` 额外补上 `safepal.com`，替换更完整。
- **OKX**：主配置为 blackmatrix7 OKX + 7 条手工补充（okx-dns/dns1/dns2、okx.ac、okx.cab、okx.com.cdn.cloudflare.net、xlayer.tech）。Blink `OKX.list` 全部覆盖，可整体替换并删除手工行。
- **Telegram**：主配置为 `PROTOCOL,MTProto` + Repcz Telegram/Telegram_NoIP 双列表（含 IP 覆盖）。Blink `Telegram.list` 仅为 SukkaW 核心域名，覆盖较窄 → 主配置**保持现状**；Blink Telegram.list 供需要最小域名集的场景使用。
- **Steam**：主配置引用 blackmatrix7 Steam；本次审计后 Blink 已新增 `Steam.list`（Repcz），可替换。
- **Apple Music / Apple 全套**：主配置直引 Repcz AppleMusic + SukkaW apple_cn/apple_cdn + 手工 Apple 补充；按既定政策暂缓，保持现状。
- **Google/Gmail、WeChat、DouYin、Emby、sub-store 等**：属基础设施、国内 App 或个人影音项，不在 Blink 范围，保持现状。
- **APTV（个人维护直播清单，原计划名 Live）**：2026-08-15 已迁入 Blink（supplement-only，26 条，迁自私有保存清单）；主配置可改为引用 `Surge/APTV.list`，策略仍由主配置指定。
- **Reject / LAN / domestic / CDN / China IP 等基础设施**：继续直接引用成熟上游，不纳入本仓库。

supplemental：不适用（本身即无 primary 上游）。

## 使用场景扩展新增 10 App（2026-08-16）

触发原因：按使用场景清单逐项对照后，发现 Disney、Paramount+、Hulu、Amazon Prime Video、HBO(Max)、Twitch、NBA、Suno、Facebook、Google(含 Gmail) 尚未覆盖。清单中的 YouTube TV 无需新增：`YouTube.list` 的 `DOMAIN-SUFFIX,youtube.com` 已覆盖 tv.youtube.com（已在 manifest note 记录）；Gemini/ChatGPT 由 `AI.list` 覆盖。以下候选证据均为当日从上游仓库直接抓取（本地 shallow clone），Repcz 与 v2fly 的维护时间以仓库分支 head / GitHub API 实测为准。

### Disney

| 候选 | 作者 | 规模/覆盖 | 维护证据 | 结论 |
| --- | --- | --- | --- | --- |
| Repcz | Repcz | 174 条，Disney+ 及 Disney 家族品牌（abc/espn/natgeo 等），Surge 原生 | 每日自动更新（分支 head 2026-08-15） | ✅ 选定 |
| blackmatrix7 | blackmatrix7 | `rule/Surge/Disney/Disney.list`，UPDATED 2025-06-06（陈旧） | 陈旧 | 备选 |
| v2fly | v2fly | `data/disney` 更新于 2026-08-05，但为 tier-4 且带 attribute 需转换 | 活跃 | 备选 |

决议：primary = Repcz `Surge/Rules/Disney.list`（174 条）。含 2 条 PROCESS-NAME（com.disney.disneyplus、com.disney.datg.videoplatforms.android.abc），对 Egern/QX 显式丢弃并计入报告。无需 supplemental。

### ParamountPlus

Repcz / SukkaW / v2fly / MetaCubeX 均无专项规则；blackmatrix7 `rule/Surge/ParamountPlus/ParamountPlus.list`（10 条：4 DOMAIN + 5 SUFFIX + 1 USER-AGENT `PPlus*`，UPDATED 2025-06-06）为全网唯一可直接使用的专项源；RuleGo 另有 `ParamountPlus.list` 但未做新鲜度实测。

决议：primary = blackmatrix7（10 条）。内容为 paramountplus.com + CBS 流媒体主机，域名稳定；note 已记录“约 14 个月旧，若使用暴露缺口再复核”。无需 supplemental。

### Hulu

| 候选 | 作者 | 规模/覆盖 | 维护证据 | 结论 |
| --- | --- | --- | --- | --- |
| blackmatrix7 | blackmatrix7 | 59 条（57 SUFFIX + 1 DOMAIN + 1 PROCESS-NAME），US/JP 范围（含 happyon.jp） | UPDATED 2025-06-06 | ✅ 选定 |
| v2fly | v2fly | `data/hulu`，GitHub API 实测 2022-10-05 起未更新 | 死亡 | 排除 |
| Repcz / SukkaW | — | 无专项（SukkaW 仅合并 stream.ts） | — | 排除 |

决议：primary = blackmatrix7（59 条）。1 条 PROCESS-NAME（com.hulu.plus）对 Egern/QX 显式丢弃。v2fly 数据四年未动，Repcz/SukkaW 无独立产物，blackmatrix7 虽 14 个月旧但为最鲜活的专项源。无需 supplemental。

### Amazon Prime Video

| 候选 | 作者 | 规模/覆盖 | 维护证据 | 结论 |
| --- | --- | --- | --- | --- |
| Repcz | Repcz | 16 条（含 6 条精确 `DOMAIN,*.cloudfront.net` 分发域名，非通配） | 每日自动更新 | ✅ 选定 |
| blackmatrix7 | blackmatrix7 | 18 条（含 1 条 KEYWORD primevideo，偏宽） | UPDATED 2025-06-06 | 备选 |
| v2fly | v2fly | `data/primevideo` 更新于 2025-11-13 | 较新 | 备选 |

决议：primary = Repcz `Surge/Rules/PrimeVideo.list`（16 条）。6 条 cloudfront/akamai 均为 `DOMAIN`（分发级唯一子域），不吞共享 CDN 命名空间。无需 supplemental。

### HBO (Max)

| 候选 | 作者 | 规模/覆盖 | 维护证据 | 结论 |
| --- | --- | --- | --- | --- |
| Repcz | Repcz | 48 条，覆盖 hbomax.com 与现行 max.com 品牌 + HBO 专属 Akamai/CloudFront 主机 | 每日自动更新 | ✅ 选定（+2 条 exclude） |
| blackmatrix7 | blackmatrix7 | HBO/HBOAsia/HBOHK/HBOUSA 分列表，UPDATED 2025-06-06 | 陈旧 | 备选 |
| v2fly | v2fly | `data/hbo` 更新于 2026-05-12 | 活跃 | 备选 |

决议：primary = Repcz `Surge/Rules/HBO.list`，manifest exclude 2 条通用 AWS API Gateway 区域后缀：
`domain-suffix:execute-api.ap-southeast-1.amazonaws.com` 与 `domain-suffix:execute-api.us-east-1.amazonaws.com`（会误伤同区域任意 AWS 服务；48 − 2 = 46 条输出）。1 条 PROCESS-NAME（com.hbo.hbonow）对 Egern/QX 显式丢弃。无需 supplemental。

### Twitch

| 候选 | 作者 | 规模/覆盖 | 维护证据 | 结论 |
| --- | --- | --- | --- | --- |
| blackmatrix7 | blackmatrix7 | 22 条：8 SUFFIX + 1 KEYWORD(ttvnw) + 11 IP-CIDR + 1 IP-CIDR6 + 1 PROCESS-NAME（no-resolve 语义完整） | UPDATED 2025-06-06 | ✅ 选定 |
| v2fly | v2fly | `data/twitch` 更新于 2026-05-05，但仅 8 条裸域名，无 IP 覆盖 | 活跃但覆盖窄 | 备选 |
| Repcz / SukkaW | — | 无专项 | — | 排除 |

决议：primary = blackmatrix7（22 条）。取舍理由：v2fly 虽新但仅域名；blackmatrix7 提供域名 + 关键字 + IP 段（直播媒体走 IP 时仍可命中）。1 条 PROCESS-NAME 对 Egern/QX 显式丢弃。无需 supplemental。

### Facebook

| 候选 | 作者 | 规模/覆盖 | 维护证据 | 结论 |
| --- | --- | --- | --- | --- |
| Repcz | Repcz | 580 条（核心 facebook 域 + 防钓鱼拼写变体，社区标准做法） | 每日自动更新 | ✅ 选定 |
| v2fly | v2fly | `data/facebook` 更新于 2026-08-05，同类拼写变体条目，无相对优势 | 活跃 | 备选 |
| blackmatrix7 | blackmatrix7 | UPDATED 2025-06-06 | 陈旧 | 备选 |

决议：primary = Repcz `Surge/Rules/Facebook.list`（580 条）。拼写变体（acebook.com 等）为防钓鱼/防错输的社区标准条目，v2fly 数据集同样携带，不构成排除理由。无需 supplemental。

### Google（含 Gmail）

| 候选 | 作者 | 规模/覆盖 | 维护证据 | 结论 |
| --- | --- | --- | --- | --- |
| Repcz | Repcz | 25 条紧凑核心：KEYWORD google + KEYWORD gmail + googleapis/gstatic/gvt/1e100 等 | 每日自动更新 | ✅ 选定 |
| blackmatrix7 | blackmatrix7 | 703 条（684 SUFFIX），含 gmail.com/googlemail.com，UPDATED 2026-05-12 | 较新但体量过大 | 备选 |
| v2fly | v2fly | `data/google` 更新于 2026-08-01，体量与 bm7 同量级 | 活跃 | 备选 |

决议：primary = Repcz `Surge/Rules/Google.list`（25 条）。`DOMAIN-KEYWORD,google` 是 google.com / googleusercontent.com 覆盖的主干——与 Instagram 排除 KEYWORD 的情形不同：真实第三方含 "google" 的域名几乎不存在（多为钓鱼站），保留收益远大于风险，manifest note 已记录此取舍。Gmail 由 `DOMAIN-KEYWORD,gmail` 覆盖（gmail.com / googlemail.com）。youtube.com 条目与 YouTube.list 自动去重。无需 supplemental。

### NBA（supplement-only）

Repcz / SukkaW / blackmatrix7 / v2fly / MetaCubeX / RuleGo 六家均无 NBA 专项规则（v2fly `data/nba` 404、bm7 `rule/Surge/NBA` 无命中、Repcz `Surge/Rules` 无命中）。

决议：supplement-only（`sources: []`）。`DOMAIN-SUFFIX,nba.com` + `DOMAIN-SUFFIX,nba.net` 覆盖官网与官方 App（api/cdn/stats.nba.com 均为 nba.com 子域）。若日后使用暴露缺失域名，按 supplement 政策（先与上游比较、只补真正缺口）追加。

### Suno（supplement-only）

六家上游均无 Suno 专项规则（v2fly `data/suno` 404、其余无命中）。

决议：supplement-only（`sources: []`）。`DOMAIN-SUFFIX,suno.com` + `DOMAIN-SUFFIX,suno.ai` 覆盖官网、移动 App 与 API（studio-api.suno.ai 为 suno.ai 子域）。若日后使用暴露缺失域名，按 supplement 政策（先与上游比较、只补真正缺口）追加。

### Starryblu（supplement-only，2026-08-26）

Starryblu 是全球支付 App（官网 starryblu.com，新加坡 FinTech 2025 参展方，App Store id 6736854716），与 ZABank 同类 Finance 场景。审计探测一梯队：Repcz `Surge/Rules/Starryblu.list` 404、SukkaW `Source/non_ip/starryblu.conf` 404、v2fly `data/starryblu` 404、blackmatrix7 `rule/Surge/Starryblu` 404 —— 四家均无专项规则。

决议：supplement-only（`sources: []`）。`DOMAIN-SUFFIX,starryblu.com` 覆盖官网与 App API 子域。若日后使用暴露缺失域名，按 supplement 政策追加。

### 落地决议汇总（2026-08-16）

- 8 个有上游的 App 全部按上表 primary 落地，均无需 supplemental；manifest `note` 已写入选择理由。
- 构建报告：Disney 174 / ParamountPlus 10 / Hulu 59 / PrimeVideo 16 / HBO 46（排除 2 条）/ Twitch 22 / Facebook 580 / Google 25 / NBA 2 / Suno 2；PROCESS-NAME 丢弃仅发生在 Egern/QX（Disney 2、Hulu 1、Twitch 1、HBO 1、Netflix 1、Spotify 1）。
- Portal：新增“网页(Web)”类别承载 Google；图标取 iTunes App Store 官方 artwork（HBO 取现行 Max 应用图标）。
- NBA/Suno 为无上游的 supplement-only App，维持两条核心根域（2026-08-16 定稿：无需专门等待真机反馈）；如日后使用暴露缺失域名，按 supplement 政策追加。

### AWSConsole（v2fly，2026-09-01）

AWS Console App（App Store `com.amazonaws.mobileConsole`，AMZN Mobile LLC）。审计探测：
SukkaW `Source/non_ip/aws.conf` 404、Repcz `Surge/Rules/AWS.list` 与 `Amazon.list` 404、
blackmatrix7 `rule/Surge/AWS/AWS.list` 404 —— 均无 AWS 专项规则；
**v2fly `data/aws` 200（唯一专项源）**，覆盖 `aws.amazon.com`、`console.aws.amazon.com` 系、
`awsapps.com`、`awsstatic.com`、`aws.com` 等完整 AWS 域名集。

数据特点与处置：

- `include:aws-cn`：China 专属子集，既正确性（国内直连默认）与范围（不吞 China 区域）考量，manifest
  `deny: ["aws-cn"]` 显式拒绝（计入 `denied_includes`）；
- `regexp:.+\.awsdns-[0-9][0-9]\.(co\.uk|com|net|org)$`：Route 53 DNS 主机模式，v1 白名单外——
  构建器新增 `regexp:*` 类型级显式排除（与 `ip-asn:*` / `url-regex:*` 同哲学），
  单测覆盖"排除成功 + 不排除报错"两条路径；
- `cloudfront.com` / `cloudfront.net`：通用共享 CDN 命名空间，按"不吞共享 CDN"政策以具体
  `domain-suffix` exclude 剔除（与 HBO 剔除 AWS API Gateway 后缀同先例）；
- 预检产出 49 条（`--app AWSConsole`），全量写入 `--accept-large-change`（新 App，审计已完成）。

决议：primary = v2fly `data/aws`；无 supplemental。manifest note 已记录完整取舍。
