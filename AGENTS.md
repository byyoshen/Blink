# Blink 项目规范

> 本文定义本仓库的工程规范与自动化边界：构建管线的约束、选源政策与安全红线。
> 供维护者、自动化工具（AI 编码助手等）与想了解构建机制的读者阅读。

## 项目目标

自动生成个人使用的多客户端 App Rule-Sets：一份 source definition 与 canonical 规则，渲染为 Surge / Shadowrocket / Loon / Stash / mihomo / Egern / Quantumult X 七个客户端的输出（格式事实与架构决策见 `engine/docs/MULTI_CLIENT_AUDIT.md`）。

## 规则与来源规范

- Generated files 不允许手工维护。
- 补充规则只能放在 `engine/sources/supplement/`。`supplement` 只存放上游规则未覆盖、且通过 Surge 日志或实际使用确认需要补充的规则。
- 不允许将上游已存在的规则重复放进 `supplement`；应先与选定上游比较，只加入真正缺失的规则。
- `supplement` 文件按需创建；没有补充规则的 App 不需要空文件。
- Generated `Surge/*.list`、`Loon/*.list`、`Shadowrocket/*.list`、`Stash/*.list`、`mihomo/*.list`、`Egern/*.yaml`、`QuantumultX/*.list` 不允许手工维护或修改；Surge / Loon / Shadowrocket / Stash 四个 classical 目录必须保持逐字节相同；`mihomo/*.list` = 对应 Surge 文件去掉 `USER-AGENT,` 行（Clash 系内核无此类型，构建器显式丢弃并计数，CI 有 golden-byte 断言）。
- 根目录 `manifest.json` 同样是 generated file，不允许手工维护；它必须确定性记录 source definition、实际上游输入、supplement、canonical 规则与七端产物 SHA256，且通过 `engine/scripts/verify_manifest.py` 校验。
- 每个 App 默认使用 1 个 primary source，最多 1 个 supplemental source，除非有明确理由。
- 不追求规则数量最大化，避免无意义吞入共享 CDN。
- Reject / Domestic / China IP / CDN / LAN 等基础设施规则不纳入本仓库，继续直接引用成熟上游。
- 输出规则不带策略名：Surge / Shadowrocket 由主配置 `RULE-SET`、Loon 由 `[Remote Rule]`、Stash 由 `rule-providers` + `RULE-SET`、mihomo 由 `rule-providers`（`behavior: classical, format: text`）+ `RULE-SET`、Egern 由 `rule_set.match` 在引用处指定策略。Quantumult X 例外：filter 行尾必有策略字段，本仓库用字面占位符 `policy`，实际策略由 `[filter_remote]` 引用行的 `force-policy` 指定（QX 的 no-resolve 槽位无生产实证，渲染时统一省略并已记入 `engine/docs/MULTI_CLIENT_AUDIT.md`）。
- `exclude` 的丢弃同样必须可审计：type-level exclude 记入 `skipped_excluded`，domain 级 exclude 记入 `manifest.json` 的 `canonical.excluded_domains`（每条声明的命中数）。某条 exclude 命中数归零意味着它可能已因上游改写而失效，需要复核上游是否仍携带该规则，或删掉这条 exclude。
- 每个客户端渲染器只允许序列化该客户端可无损表达的规则；无法表达时必须显式丢弃并在构建报告计数（降级项：PROCESS-NAME 对 Egern / Quantumult X 显式丢弃并计数，USER-AGENT 对 mihomo 显式丢弃并计数；classical 输出保持 Surge / Loon / Shadowrocket / Stash 四端逐字节相同、保留 PROCESS-NAME 行——Loon / Shadowrocket 无此类型，客户端直接忽略），禁止静默转换。

## Upstream Source Selection Policy

- 上游优先偏好（长期验证的信任顺序）为：SukkaW > Repcz > 其他长期验证过的成熟作者 > v2fly / MetaCubeX。
- SukkaW 与 Repcz 均属于一梯队可信上游。SukkaW（skk）的 App 专项规则先审；Repcz 的专项或可直接适用的窄范围规则随后必审，不能在执行中被降为普通 fallback。
- SukkaW 的基础设施规则和配置方法本身具有长期价值；但 Reject / Domestic / China IP / CDN / LAN 等通用基础设施仍应直接引用成熟上游，不能为了 App 覆盖把通用规则集复制或误归类为 App 专项规则。
- 此排序是优先偏好，而非绝对规则。每个 App 的最终主源必须基于 freshness（更新活跃度）、completeness（覆盖完整度）、scope（是否精准属于该 App）、format suitability（是否适合 Surge 或能稳定转换）及 maintenance quality（维护质量）综合决定。
- 如果 Repcz 或 SukkaW 有对应且维护良好的专项规则，优先使用。
- 如果 Repcz 或 SukkaW 没有对应规则，或规则明显长期未更新、覆盖不足，则可以选择 v2fly / MetaCubeX 等更活跃的数据源。
- 不允许仅因作者偏好而继续使用明显过时或不完整的规则。
- 后续 `apps.yaml` 应为每个 App 保留 `note` 或 `reason` 字段，记录主源的选择理由，避免决策依据遗失。
- 真正创建 `apps.yaml` 前，必须先完成 source audit。

### Source audit 范围与记录项

- Source audit 至少覆盖当前计划中的 YouTube、X、Instagram、Threads、Telegram、AI、TikTok、Spotify、Netflix、OKX、PayPal、SafePal、ZABank、WhatsApp、LINE、GitHub；原清单中的 Live（现命名 APTV）为个人维护的直播源，2026-08-15 起以 supplement-only 形式纳入（`sources: []`，未经过上游审计）。2026-08-16 使用场景扩展新增的 Disney、ParamountPlus、Hulu、PrimeVideo、HBO、Twitch、Facebook、Google、NBA、Suno 已按同一流程完成审计并落地（NBA/Suno 无上游，supplement-only；完整档案见 `engine/SOURCE_AUDITS.md`）。
- 每个 App 的 audit 必须记录：候选来源、作者、URL、最近维护情况、规则规模或覆盖特点、是否 Surge 原生、是否需要转换、是否存在明显过宽规则、推荐 primary、是否需要 supplemental，以及选择理由。

## 安全规范

- 禁止提交机场订阅 URL、token、GitHub PAT、密码、2FA、MTProto secret、证书等敏感信息。
- 提交前对变更文件做敏感模式自检：GitHub PAT（`ghp_`/`github_pat_`）、AWS Key（`AKIA…`）、私钥/证书块（`-----BEGIN … PRIVATE KEY-----`）、机场订阅 URL 与代理协议链接（`vmess://`/`vless://`/`ss://`/`trojan://` 等）、URL 内嵌凭据（`?token=`/`user:pass@`）、本地绝对路径（如 `C:\Users\<用户名>`）一律不得进入提交；发现仓库既有的敏感痕迹先报告再处理，不自行删除或改写历史。

## Profile 层规范（配置迁移）

- Rules 自动更新（每日 Actions），Profiles 人工演进：`engine/sources/profile/` 与 `Profiles/` **绝不加入** `update.yml` 定时任务，Profile 修改不自动 Commit，每次提交由维护者人工确认。
- 语义源是 `engine/sources/profile/intent.yaml`（Canonical Profile Intent），不是 Surge 配置文本；迁移的是配置意图。
- 普适性原则：公开 Profile 只含**单一订阅池**（占位 URL `https://YOUR-SUBSCRIPTION-URL`，真实订阅地址绝不进入仓库）；个人专属内容（多订阅池、个人域名等）保留在本地副本，不进入 intent 与公开输出。
- 能力映射只允许 FULL / ADAPTED / UNSUPPORTED 三种结果；UNSUPPORTED 与 ADAPTED 必须在生成文件中以注释显式标注（例如 Egern url-test 暂以 select 呈现），禁止静默删除或伪造。
- 采用横向切片开发：一次只做一个功能 × 七客户端，验证后再做下一个；实施顺序与决策依据见 `engine/docs/PHASE_OPTIMIZATION_PLAN.md` 与 `engine/STATUS.md`。
- 配置文件输出 `Profiles/` 为生成产物（含占位符），修改入口是 intent 与 templates，改后运行 `engine/scripts/build_profile.py --write` 重建。

## 可用工具与 Git 规范

- 开发验证使用本地 filesystem、terminal、Git CLI 与 Chrome；不依赖在线插件。
- 执行会修改 Git repository 状态的命令前，先说明该命令用途。
- 禁止未经确认使用 `git reset --hard`、force push、改写已发布历史。

## 测试规范

- **禁止给 UI 写单元测试。** 断言「某组件渲染了某字段」「某元素带了某 class」
  的测试不是测试，是**变更检测器**：它们不描述行为，只拍下当前形状，代码一重构
  就得跟着改。这类测试是**负资产** —— 它提高了改动成本，却不提高发现缺陷的概率。
- 测试要测**行为与函数**，不测形状。把 mock 数据喂进去再断言它原样出来，
  验证的只是测试自己。优先写集成测试：走真实输入 → 真实管道 → 可观测输出。
- **UI 验收一律由维护者人工完成。** agent 改完前端后的交付物是：受影响界面清单
  ＋逐条可执行的验证 Todo（看哪里、怎么操作、期望什么），而不是一句「已验证」。
- **禁止 agent 用 computer use / 浏览器自动化做 UI 验收。** 包括截图、点击、DOM 查询、
  computed style 量测 —— 默认一律不做。确有必要时先说明理由并**等待维护者明确确认**，
  获授权后才能执行；授权只对当次生效，不自动延续到下一次。
- 不受此限制的仍然必须跑：`tsc` / `prettier --check` / `vite build` / `ruff`，以及一切
  不涉及 UI 外观的离线门禁（见 `engine/docs/MACHINE_GATES.md`）—— 它们测的是能不能构建与
  产物是否一致，不是界面好不好看。

## 开发顺序

- 首批开发顺序：OKX、WhatsApp、LINE、GitHub；它们只是 source → build → supplement → Surge output 整个 pipeline 的验证样本，不代表它们优先于其他 App，也不代表仓库只面向这四个 App。仓库设计上应支持当前计划中的全部 App。
- OKX 此前列出的 10 个域名仅是待核对候选；必须先与选定上游比较，只把真正缺失项加入 `engine/sources/supplement/`。
- Apple Music 暂缓，因为当前 Apple 分流依赖 Repcz、Sukka、extended-matching 和手工 CDN 修复。

## 高效且保守的新增 App 流程

- 新 App 的 source audit 可以按产品类别批量开展，但每个 App 必须保留独立的候选、证据和 primary 结论。
- 审计时按一梯队顺序先检查 SukkaW（skk）专项规则与 Repcz 专项规则（或可直接适用的窄范围规则）；只有两者不存在、长期缺乏维护、范围不准或格式不适合时，才按证据比较其他成熟作者、v2fly 或 MetaCubeX。若候选规则规范化后等价，作者优先偏好作为 tie-breaker。
- 新 App 在 manifest 提交前，优先执行定向只读预检：`build.py --app <App>`。不要因为一个新增 App 而在本地重复阻塞于所有既有上游的网络状态。
- 全量预检仍是必要的健康检查，但应放在 GitHub Actions、每日更新、发布前检查或明确的全仓库验证中；生成动作必须继续保持“所有选定 App 都成功后才写输出”的原子性。
- 本地验证优先复用被 `.gitignore` 排除的 `.venv` 与锁定的 `requirements.txt`，避免重复下载依赖；`.venv` 绝不提交。
- 不默认缓存上游规则文本。任何未来的缓存必须具有显式 TTL、内容指纹、失效策略，并确保 GitHub Actions 的发布构建仍从上游重新获取，避免缓存掩盖真实上游变化。
- 全量写入默认启用供应链变化门禁：单 App 新增或删除超过 20 条、语义变化比例超过 20%、或出现新规则类型时，在写入前失败。只有完成人工 source audit 后才可显式使用 `--accept-large-change`；完整门禁与命令见 `engine/docs/MACHINE_GATES.md`。
