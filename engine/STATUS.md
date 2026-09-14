# Blink 项目状态

> 本文是仓库当前状态的维护者侧摘要，不重复 README 的对外说明。规则与来源规范见
> [AGENTS.md](../AGENTS.md)，七端格式事实见 [docs/MULTI_CLIENT_AUDIT.md](docs/MULTI_CLIENT_AUDIT.md)，
> 机器门禁见 [docs/MACHINE_GATES.md](docs/MACHINE_GATES.md)，规则模型的 DNS 语义与顺序不变式见
> [docs/DNS_SEMANTICS.md](docs/DNS_SEMANTICS.md)，完整选源档案见 [SOURCE_AUDITS.md](SOURCE_AUDITS.md)。
>
> 本文档不包含任何订阅 URL、token、凭据或本地路径。

## 项目身份

- 名称：**Blink**；GitHub：<https://github.com/byyoshen/Blink>；Pages：<https://byyoshen.github.io/Blink/>。
- 沿革：仓库曾用名 `WProxyRules`、`Rulink`，2026-08-15 改为 Blink；账户曾用名 `Bluetrae`，
  现已迁移为 `wendy1a1a`，2026-09-11 迁移为 `byyoshen`——GitHub 对旧账户路径（含 raw / Pages）提供 301 重定向，
  仓库内不再引用旧名称。

## 当前状态（2026-09-01 更新）

- **数据面**：30 个 App、27 个实际读取的上游输入、210 个七端主产物；`manifest.json` 确定性记录
  每 App 的 source definition、上游输入指纹、supplement、canonical 规则与七端产物 SHA256，并额外记录
  per-client 语义视图（domainset / nonip / ip）。
- **规则层 multi-view**：`build.py` 的 `semantic_views()` 把 canonical 按「非 IP 段在前、IP 段在后」
  派生为至多两个视图 —— 非 IP 段整体只有 `DOMAIN` / `DOMAIN-SUFFIX` 时产出 `-domainset.conf`
  （裸域名清单），一旦含 `DOMAIN-KEYWORD` / `USER-AGENT` / `PROCESS-NAME` 就改为产出 `-nonip.conf`
  （classical 规则行）；**两者互斥**，同一 App 只产出其中之一，空视图不产出。有 IP 规则时另有
  `-ip.conf`。实测当前 30 个 App 为 17 个 `-domainset.conf` + 13 个 `-nonip.conf`，无一同时具备；
  权威定义见 `engine/scripts/validate_views.py` 的 `VIEW_KINDS`。
  Surge / Shadowrocket 为域名清单、Stash / mihomo 为 `behavior:domain`、Loon / Egern 为 classical、
  QX 为 `HOST*` filter；`validate_views.py` 门禁已接入 `checks.yml` 与每日 `update.yml`。
- **Profile 层**：`intent.yaml` 收敛为普适八组（单一订阅池 + 地区组 / Auto + Proxy / Final + 6 个 App 路由），
  7 端模板能力矩阵 FULL / ADAPTED(注释) / UNSUPPORTED(注释) 标注；`Profiles/` 为生成产物，
  修改必须人工确认后提交，不进入每日更新。
- **Portal**：规则集 / 接入 / 配置文件 / 构建与来源四个板块；七客户端切换、官方 App 图标、
  统一复制菜单、App 搜索；主题默认深色、支持手动切换，favicon 为仓库自绘 IP。
- **门禁**：`checks.yml`（push / PR）运行单测、parity、health、validate_views、overlap 基线、
  manifest、Profiles 引用、敏感模式、golden-byte、Python lint 与 Portal prettier / typecheck；
  `update.yml`（每日）实时抓取上游并在全部门禁通过后写入提交。当前 overlap 基线为 4 对 App、21 条
  （AI×X、Facebook×Instagram、Facebook×WhatsApp、Google×YouTube）。
- 最新提交以 `git log` 为准；2026-08-15 后的变更沿革可在 `git log origin/main..main` 中查看。

## 仓库结构

```text
# 产品输出（根级，raw URL 稳定）
Surge/                      # classical .list（原 Surge 入口，路径与字节不变）
Loon/                       # 与 Surge 逐字节相同的 classical .list
Shadowrocket/               # 与 Surge 逐字节相同的 classical .list
Stash/                      # 与 Surge 逐字节相同的 classical .list
mihomo/                     # classical 去掉 USER-AGENT 行（其余逐行同 Surge）
Egern/                      # Egern 自有 YAML Rule-Set schema
QuantumultX/                # QX filter 行（行尾占位符 policy，由 force-policy 覆盖）
Profiles/                   # 七客户端完整配置文件（人工维护层，订阅占位符）

# 根文件
README.md · LICENSE · AGENTS.md · DISCLAIMER.md · THIRD_PARTY_NOTICES.md · manifest.json · .gitignore · .github/

# 构建引擎与开发侧（全部收敛于此）
engine/
├── scripts/                # build.py / renderers.py / build_profile.py / gen_portal_stats.py
│                           # + repo_identity.py（owner/repo slug 的唯一来源）与各门禁脚本
├── sources/                # apps.yaml、supplement、profile intent 与 templates
├── tests/                  # 单元测试
├── portal/                 # 网页门户（Vite + React + TS + Tailwind CSS）
└── docs/                   # 格式审计、机器门禁、设计蓝图与静态资源
```

## 文档与事实优先级

信息不一致时按以下顺序判断（低优先级不得覆盖高优先级）：

1. 当前 Git 工作区、`git status`、Git 历史与已生成文件；
2. `engine/sources/apps.yaml`、`engine/scripts/*.py`、测试与 workflow；
3. `AGENTS.md`、README 与合规文档（DISCLAIMER / THIRD_PARTY_NOTICES）；
4. 本文件；
5. 历史文档中可能残留的废弃设计或临时推测，仅作追溯，不作依据。

## 构建器关键语义

- `build.py` 默认只检查（含全部客户端渲染验证）；仅显式 `--write` 才写入生成目录。
- 输入格式：`v2fly-domain-list` 与严格白名单的 policy-free `surge-rule-set`（仅 DOMAIN /
  DOMAIN-SUFFIX / DOMAIN-KEYWORD / USER-AGENT / PROCESS-NAME / IP-CIDR / IP-CIDR6，IP 只允许额外
  no-resolve）；v2fly `domain` / `full` / `keyword` 分别映射为 `DOMAIN-SUFFIX` / `DOMAIN` /
  `DOMAIN-KEYWORD`。
- v2fly include 采用显式 allow / deny policy：未声明的 include 或同时 allow / deny 都会构建失败；
  `@!` 否定属性不被支持，必须显式失败；带 attribute 的条目默认跳过。
- exclude 是 manifest 的显式决策（类型级 `ip-asn:*` / `url-regex:*` 等），不能以猜测替代 source audit。
- 上游完全缺失的 App 可声明 `sources: []`（supplement-only），全部规则来自
  `engine/sources/supplement/<App>.list`；最终输出仍必须非空。
- 渲染器：`classical`（Surge / Loon / Shadowrocket / Stash 四端逐字节相同）、`classical-mihomo`
  （去 USER-AGENT，显式丢弃并计数）、`egern-yaml`（PROCESS-NAME 显式丢弃并计数）、`quantumultx`
  （`HOST*` / `IP-CIDR` / `IP6-CIDR` / `USER-AGENT`，行尾占位符 `policy`，no-resolve 统一省略）；
  所有显式丢弃均计入构建报告，禁止静默转换。
- Surge 向后兼容门禁：`Surge/*.list` 路径与字节自 v1 起不变，重构建后 `git diff Surge/` 必须为空。

## 已确定的规则源结论

各 App 的权威定义（URL、格式、exclude / include / attribute policy）与精简理由见
`engine/sources/apps.yaml` 的 `note`；完整审计档案见 `SOURCE_AUDITS.md`。摘要如下：

| App | Primary / 方案 | 一句话理由 |
| --- | --- | --- |
| OKX / WhatsApp / LINE / GitHub / SafePal / Threads / AWSConsole | v2fly `domain-list-community` | 覆盖比旧源更现代、范围精准；GitHub 显式 allow `github-copilot`、deny `npmjs`；AWSConsole 来自 `data/aws`（`aws-cn` 显式拒绝、awsdns regexp 与共享 CDN 显式排除） |
| PayPal / YouTube / X / Instagram / TikTok / Spotify / AI / Steam / Disney / PrimeVideo / HBO / Facebook / Google | Repcz `Surge/Rules/` | Surge 原生、每日更新、范围精准；个别类型经 manifest 显式 exclude |
| Telegram | SukkaW `Source/non_ip/telegram.conf` + SukkaW ruleset service `ruleset.skk.moe/List/ip/telegram.conf`（补充 IP 段） | 核心域名 + 官方 Telegram CIDR，domain / IP 两段 |
| Netflix / ParamountPlus / Hulu / Twitch | blackmatrix7 `rule/Surge/` | 保留 IP 覆盖与 no-resolve 语义；部分为全网唯一专项源（需定期复核新鲜度） |
| ZABank / NBA / Suno / Starryblu / APTV | supplement-only（`sources: []`） | 无可用上游；APTV 为个人维护的直播清单（迁自私有保存，不属第三方上游） |

各端显式降级计数（PROCESS-NAME → Egern / Quantumult X；USER-AGENT → mihomo）体现在构建报告与
`manifest.json`，portal 卡片同步展示。

## 无人值守与人工介入时机

- **每日自动（北京时间约 00:01 的 GitHub Actions）**：拉取上游 → 单测 → 全量重建 → 仅生成目录或
  门户数据有实质变化时由 bot 提交；无变化零提交。GitHub 定时任务不保证准点。
- **构建失败 = 暂停更新，不是故障**：上游 404 / 超时 / 格式不合时构建显式失败且不写任何文件，
  旧输出继续可用；下次维护时修复即可。
- **需要人工介入**：Actions 失败排查；新增 App（source audit → `apps.yaml` → 定向预检 →
  提交）；日志发现漏网（确认归属 → 与上游比较 → 写 supplement → 重建）。
- 建议开启仓库 Actions 失败通知（Watch → Custom → 勾选 Actions）。

## 已知待办与谨慎项

- Phase 2+ 横向切片（Region / Node Filters 细化、DNS、MITM 等）按 `docs/PHASE_OPTIMIZATION_PLAN.md`
  顺序推进；真机 E2E 验证清单：策略组显示 / 成员 / 切换 / 日志确认，以及 Egern url-test（当前
  ADAPTED 为 select）验证。
- Apple Music 暂缓：当前 Apple 分流仍依赖 Repcz、SukkaW 与 extended-matching 等手工 CDN 组合，
  暂不纳入此 pipeline。
- 漏网规则处理流程：

```text
Surge 日志出现漏网
→ 确认 App 归属
→ 与选定上游比较，确认缺失
→ engine/sources/supplement/<App>.list
→ 重新构建并验证
→ 此后作为永久保留
```
