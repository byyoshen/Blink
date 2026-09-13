# Blink 工程审查记录 · 2026-09-12

> 一次全仓库只读审查 + 四批修复的完整结论。写成**可证伪的登记表**：每条结论都标明
> 证据、修复落点和**验证强度**，末尾给出独立复核者可直接执行的命令。
>
> 这不是设计文档。格式事实以 `MULTI_CLIENT_AUDIT.md` 为准，门禁机制以
> `MACHINE_GATES.md` 为准，规则与选源规范以 `AGENTS.md` 为准。
>
> **修订**：
> 
> - 2026-09-13 —— F9 由推断改为实证，O2 关闭。审查结论本身未变。
> - 2026-09-13 —— portal 覆盖度由 37% 提到 54%（`Nav.tsx` / `hooks.ts` 逐行审完），
>   新增 F14。盲区结论本身被证实，未变。
> - 2026-09-13（收尾）—— portal 剩余 433 行审完，**覆盖度 100%**，新增 F15；
>   O1 关闭，新开 O8。
> - 2026-09-13（重命名）—— 第 7 个客户端由 **Clash 改名为 mihomo**（目录 `Clash/` → `mihomo/`，
>   `Profiles/Clash.yaml` → `Profiles/mihomo.yaml`）。**本文件下文保留旧名不改** ——
>   这是一份有日期的可证伪登记表，改写已记录的证据等于伪造当时的观测。
>   读到 F1 / F13 里的「Clash」时，指的就是现在的 mihomo。

## 审查范围

审查基线：`55076c6`。修复落在 `8d10ed3` / `c36bd48` / `167e609` / `94e2ab0`（PR #1，rebase 合并）。

### 覆盖度（含明确盲区）

| 区域 | 覆盖 |
| --- | --- |
| `engine/scripts/*.py` | 全部逐行 |
| `engine/tests/*.py` | 全部 |
| `.github/workflows/*.yml` | 全部 |
| `engine/sources/apps.yaml`、`profile/intent.yaml` | 全部 |
| `AGENTS.md`、`README.md`、`MACHINE_GATES.md`、`PHASE_OPTIMIZATION_PLAN.md`、`STATUS.md` | 全部 |
| `MULTI_CLIENT_AUDIT.md` | 按主题检索，未逐行 |
| `engine/portal/src/`（1992 行） | **100%** —— 全部逐行审完（2026-09-13 分三次：37% → 54% → 100%）。该盲区已关闭 |
| **`engine/SOURCE_AUDITS.md`（310 行）** | **0** —— 选源判断全部来自 `apps.yaml` 的 `note` 字段，未核对档案本身与 apps.yaml 是否一致 |
| **`engine/sources/profile/templates/`（7 个）** | **部分** —— 只读了 `loon.conf` 头部与全部生成结果，未逐个审模板的 General / DNS 段 |

**盲区结论**：portal 是最可能仍藏有问题的区域。TypeScript 占仓库 26.9%，审查密度远低于 Python；30 App × 7 客户端的接入片段生成逻辑只验证了 `behavior: domain` 一条分支。

> **该预测已被完整检验（2026-09-13）**：portal 分三次审完，两次都出了真缺陷 ——
> `Nav.tsx` + `hooks.ts` 给出 F14（功能永久失效的时序缺陷），最后 433 行给出 F15
> （线上 404）。盲区被宣布为高风险，两次坐实。
>
> 同时要记住这是**循环论证的反面**：盲区关闭不等于 portal 干净，只等于
> 「人读过一遍」。F15 那类问题能活到今天，正是因为人眼审阅不可靠；真正的收尾
> 是那道新门禁（`RepoDocLinkTests`），而不是覆盖度数字。

## 结论登记表

验证强度定义：

- **实证** —— 有可复现的命令或输出支持
- **文档依据** —— 依赖仓库内审计文档或上游官方文档的记载
- **推断** —— 基于已知机制的推理，尚无本仓库内的实证

### 影响正确性 / 安全

#### F1 · `no-resolve` 在 Profile 层静默丢失 · 实证 · `8d10ed3`

`PHASE_OPTIMIZATION_PLAN.md` 能力矩阵声明 Surge / Shadowrocket / Loon / Stash / Clash 对 `no-resolve` 均为 FULL，实现只给了 Surge（App IP view）与 Surge + Clash（infrastructure）。

证据：`curl https://ruleset.skk.moe/List/ip/china_ip.conf` → 3902 行有效规则，**携带行内 `no-resolve` 的 0 条**（skk 的约定是放在引用处）。因此 Stash / Shadowrocket 上走到 IP 段的域名会被本地提前解析。`Clash.yaml` 内部另有自相矛盾：`china_ip` 带该选项而 `X_ip` 不带。

修复：`IP_NO_RESOLVE_CLIENTS` 成为该能力判断的唯一实现点；Loon 因 `[Remote Rule]` 引用行无槽位，改为显式 ADAPTED 标注，能力矩阵该格由 FULL 改为 ADAPTED（仅行内）。

**验证缺口**：Shadowrocket / Stash 引用行第 4 个字段的支持性已由维护者真机确认（2026-09-12），但尚未回写 `MULTI_CLIENT_AUDIT.md`（该文档对 Shadowrocket 的实证仍是内联规则形式）。见 O1。

#### F2 · Egern renderer 在无 mixing 时误报并中断构建 · 实证 · `167e609`

`ip_has_no_resolve` 是 bool 列表，旧判据 `ip_has_no_resolve and not all(...)` 在「IP 规则全部不带 no-resolve」时为真（`[False]` 非空且 `not all` 为真），抛出 mixing 错误。docstring 与 `MULTI_CLIENT_AUDIT.md` 都写明的第三条分支（全不带则省略）从未可达。判据改为 `any(...) and not all(...)`。

#### F3 · IP 规则被静默规整 · 实证 · `94e2ab0`

`ipaddress.ip_network(strict=False)` 改写 host bits 置位的 CIDR。真实一例：上游 `Repcz/Tool/X/Surge/Rules/Twitter.list:30` 写 `IP-CIDR,104.244.42.0/21`，Blink 产物 `Surge/X-ip.conf:4` 为 `IP-CIDR,104.244.40.0/21`。范围与宽松客户端解读一致（无语义变化），缺的是可见性。现记入构建报告 `rewritten_ip_rules` 并在 stderr 提示，不中断构建。

### 会让构建或每日管线错误失败

#### F4 · QX renderer 对 `kind: domain` 报错误的错 · 实证 · `8d10ed3`

`add_rule_entry` 缺 `return`，落入只适用于 remote rule set 的 `qx_url` 必填检查。七端中仅 QX 失败。当时 intent 无此类条目，属潜伏陷阱。

#### F5 · 孤儿 view 文件使每日管线自锁 · 实证（沙箱） · `c36bd48`

`semantic_views()` 省略空视图，App 失去最后一条 IP 规则、或 `nonip` 因 keyword 消失变为 `domainset` 时留下孤儿文件，`validate_views` 判为 spurious（沙箱复现：`views check failed: GitHub/ip: spurious in Surge`），此后每日构建持续失败直到人工删除。`--write` 现按 `<App>-<view>.conf` 确定命名清理并记入 `pruned_views`。

#### F6 · 改动构建器即让 CI 失败 · 实证 · `c36bd48`

manifest 记录 `build.py` / `renderers.py` 的 SHA256，重建过去只能靠联网 `--write`，把当天上游内容变化拖进代码提交。新增 `--refresh-provenance`：离线重算 + 自证输出未变 + 越界时拒绝。

#### F7 · builder 指纹取运行中那份而非仓库内那份 · 实证 · `c36bd48`

`Path(__file__)` 与 `verify_manifest` 解析的 `root/engine/scripts/` 不一致；从仓库外运行会写入错误指纹。

### 可审计性与 CI 缺口

#### F8 · domain 级 exclude 完全无痕 · 实证 · `c36bd48`

type-level 记在 `skipped_excluded`，domain 级命中后直接 `continue`。HBO 的 `input_rules 48 → rules 46` 无法区分 exclude 与去重。现按声明逐条计入 `canonical.excluded_domains`。实测当前 5 条各命中 1 条（Instagram 1、HBO 2、AWSConsole 2）。零命中在 stderr 警告但不阻断。

#### F9 · 每日提交的门户数据永不部署 · 实证（2026-09-13 补证） · `8d10ed3`

`update.yml` 用默认 `GITHUB_TOKEN` push，该类 push 不触发其他 workflow（GitHub 文档化行为）；`pages.yml` 仅监听 `push: paths: engine/portal/**`。加 `workflow_run` 触发（仅 success）。

本条在审查当日只有推理、没有本仓库内的证据，因此原记为**推断**。2026-09-13 由第一次经过该路径的每日更新补上实证：

```text
09-12 18:12Z  Update Rule-Sets [schedule]                   success
09-12 18:13Z  Deploy portal to GitHub Pages [workflow_run]  success
```

每日更新成功后一分钟内，`workflow_run` 自动触发了一次 Pages 部署。修复成立，O2 关闭。（cron 声明 16:01，实际 18:12 才起跑 —— GitHub 对 schedule 事件在高峰期的排队延迟，与本结论无关。）

#### F10 · 无门禁保证 `stats.json` 与产物同步 · 实证 · `8d10ed3`

新增 `gen_portal_stats.py --check` 并接入 `checks.yml`；顺带修 `--stdout` 在 GBK 控制台的 `UnicodeEncodeError`。

#### F11 · 缺 `.gitattributes` · 实证 · `8d10ed3`

`core.autocrlf=true` 使工作区为 CRLF，而 manifest 记 LF 字节 SHA256 → 维护者本地无法运行自家 provenance 门禁（复现：`AI` 的 7 个产物全部 checksum mismatch）。反向风险：CRLF 进仓库后 CI 只有 `verify_manifest` 会红，按文本读取的 `parity_check` 与 golden-byte 仍绿，误导排查。CI 已实证：Linux 全新 checkout 下 `verify_manifest` 通过，`outputs: 210`。

#### F12 · slug 散落 11 处（代码）+ 18 处（手写文档） · 实证 · `167e609` `94e2ab0`

收敛进 `repo_identity.py`；新增扫描 README / 门户外壳 / 设计文档 / `Profiles/`（88 处自引用）的门禁。`verify_profiles` 的 raw URL 正则尤其危险 —— 漏改会使其匹配不到任何东西从而什么都不校验，故该扫描同时断言匹配数下限。门禁有效性已用变异测试确认（注入旧 owner 即精确报出文件与 slug）。

#### F13 · Stash / Clash 无视声明的 `phase` · 实证 · `167e609`

inline 规则被收进 `local_rules` 统一追加到 IP 段之后，改为就地输出。影响有限（`DST-PORT` 不需要 DNS），但破坏了「同一份意图跨七端一致」。

### 门户（portal）

> 本节来自 2026-09-13 对 `Nav.tsx` / `hooks.ts` 的补审，不属于 09-12 那轮全仓库审查。

#### F14 · 导航滚动定位在挂载时就死锁 · 实证 · `bc20c8f`

`useActiveSection` 的 effect 在 `<Nav>` 挂载时跑，而四个 section 要等 `stats.json` fetch
回来后才渲染。挂载那一瞬 `getElementById` 全返回 `null`，`elements.length === 0`
提前 return，IntersectionObserver 从未创建；依赖数组又永不变化，**effect 再也不会重跑**。
不是闪烁，是永久失效。修法是把「section 是否已存在」显式作为 `sectionsMounted` prop 传入，
而不是让 hook 去猜。

可复现：设置网络限速后加载页面，滚动至任一 section，导航项全不高亮（修前）。
验证：修后逐区块 DOM 查询 `aria-current`，hero 不点亮任何项，
`rulesets` / `usage` / `profiles` / `about` 各自点亮正确项。

**取样偏差提醒**：这是补审 329 行就撞到的第一个缺陷，不能据此推算剩余 portal
代码的缺陷密度 —— `Nav.tsx` 正好是当时在改的文件，看得比其他部分仔。

#### F15 · 页脚「审计档案」是线上 404 · 实证 · 收尾批

`Footer.tsx` 把「审计档案」指向仓库**根目录**的 `SOURCE_AUDITS.md`，而该文件实际在 `engine/SOURCE_AUDITS.md`。
已在生产站点上 404。

**为什么所有现有门禁都没拦住**：slug 是对的（`test_repo_identity` 只查 owner/repo），
URL 形式是合法的，`secret_scan` / `verify_profiles` 都不管路径存在性 —— 只有 GitHub 知道
它是 404。这是一个**没有任何机器在看**的缝隙。

修复：改正路径，并新增 `RepoDocLinkTests` —— 扫描所有 `blob|tree/main/<path>` 引用并断言
路径在仓库中存在，同样带匹配数下限。变异测试已确认有效：重新注入旧路径即精确报出
`engine/portal/src/components/Footer.tsx -> SOURCE_AUDITS.md`。

**该门禁的已知局限**：它扫的是文本，分不清「活链接」与「被引用举例的坏链接」。
本条 F15 初稿就因为原样转录了那个坏路径而把新门禁打红。结论是：**登记表描述坏链接，
不复现坏链接**。不为此加白名单 —— 白名单会同时放过真的坏链接。

同批顺带（不单独立条，均为一致性问题）：`Footer.tsx` 的吉祥物交叉淡入仍从 `scale-0`
开始（Nav 已改为 `scale-50`，页脚那份是第四份手抄副本，漏改）—— 已提成共享组件
`MascotSwap.tsx`；`About.tsx` 的两个文档链接是全站仅有的无样式 `<a>`，深色主题下几乎
不可读。

## 验证结果（2026-09-12）

```text
unittest                      96 tests OK              （基线 54）
ruff check / format --check   PASS
portal tsc / prettier / build PASS
parity / health / views / overlap / manifest / profiles / portal --check   全 PASS
secret_scan（CI 干净树）       558 files, 0 hits
build.py --verify-only（联网重建 27 个上游）             exit 0
CI（PR #1，4 个 job）          全部 pass
```

**产物影响**：Rule 层 476 个生成产物（210 主产物 + 266 view）**逐字节未变**；`Profiles/` 只有 `no-resolve` 与一行 `DST-PORT` 位置变化；`manifest.json` 只增加 `excluded_domains` 与 builder 指纹。

**`--refresh-provenance` 正确性的强证据**：batch 2 代码改完后离线重建出的 manifest 与已提交版本只差 `build.py` 一个指纹 —— 27 个上游指纹、210 个产物 checksum、266 个 view checksum、30 个 canonical 指纹全部离线复现。

## 未闭环

**O1 · 真机证据未回写 `MULTI_CLIENT_AUDIT.md`**（F1）—— **已于 2026-09-13 闭环**
Shadowrocket 与 Stash 章节各新增「引用行 no-resolve」条目（维护者真机确认 2026-09-12），
§4 新增「引用行 no-resolve 槽位」行，并显式区分行内与引用行两种形式 —— 把两者当成
同一件事正是 O1 的成因。回写过程中发现 Surge 存在同类缺口，见 O8。

**O2 · `pages.yml` 的 `workflow_run` 尚无本仓库实证**（F9）—— **已于 2026-09-13 闭环**
2026-09-12 18:12Z 的每日更新成功后，18:13Z 出现 `event=workflow_run` 的 Pages 部署并成功。详见 F9。
条目保留而非删除：这份文件是登记表，一条推断最后被证实还是被推翻，本身就是要记的内容。

**O3 · 当前代码的 `--write` 路径未在生产执行过**
batch 2 那次真实 `--write` 在 batch 3 / 4 的改动之前；之后只跑过 `--verify-only`（不走 write / prune）。`write_outputs → write_client_views → prune_stale_views` 在当前代码下仅有单元测试（沙箱）覆盖。

**O4 · Egern 的 `-ip.conf` view 未验证**（本次改动之前即如此）
该文件是带行内 `no-resolve` 的 classical 文本，而 Egern 的 `no_resolve` 是 set 级，能否容忍行内选项未经真机确认。

**O5 · Loon 的外部 `china_ip` 仍暴露**
`[Remote Rule]` 引用行无 no-resolve 槽位，仅加了诚实标注。根治需换成行内带 `no-resolve` 的上游 IP 规则集 —— 属选源决策。

**O6 · `secret_scan.py` 扫文件系统而非 git tracked 集合**
任何未跟踪的本机文件都能让它假红。改为扫 tracked + staged 会缩小「提交前自检」的覆盖面，是取舍问题，未擅自改动安全门禁的 scope。

**O7 · `overlap_check` 的 `removed_since_baseline` 只报不管**
基线会残留已消失的交集；若某交集消失后重现将不被拦截。「发现减少即失败」会重造 F5 那类自锁，正确做法是定期人工 `--write-baseline`，属流程而非代码。

**O8 · Surge 引用行的 `no-resolve` 槽位无依据**（回写 O1 时发现）—— **已于 2026-09-13 闭环**
维护者真机确认 `RULE-SET,<URL>,<policy>,no-resolve` 在 Surge 上生效，
代码（`IP_NO_RESOLVE_CLIENTS` 包含 surge）无需改动，已回写 `MULTI_CLIENT_AUDIT.md` §2 与 §4。
结论：官方语法列表的 `[,pre-matching][,extended-matching]` **不是穷举** ——
这本身是值得记的一条：以后不能把该文档的可选项列表当作完整集合来反推「不支持」。

## 明确不做

**把 `PORTAL_META` 并入 `apps.yaml`** —— 不做。

`apps.yaml` 是规则层的 Source of Truth，且其 SHA256 进 manifest；`PORTAL_META` 自身注释写明是 display-only（Source logic lives in the manifest）。把展示层元数据并入构建的语义源是**合并关注点而非解耦**。现状已 fail loudly（漏加即 `PortalError`），收益仅「新增 App 少改一个文件」。

**`--strict` / `--strict-diff` 的 argparse 参数** —— 保留。

已从 workflow 与文档移除（它们是 no-op，暗示 strictness 可关闭），但参数继续接受，以免破坏外部脚本或既有命令习惯。

## 如何证伪（给独立复核者）

全部离线，除最后一条：

```bash
python -m unittest discover -s engine/tests -v
```

```bash
ruff check engine/ && ruff format --check engine/
```

```bash
python engine/scripts/parity_check.py --root . && python engine/scripts/health_check.py --root . && python engine/scripts/validate_views.py --root . && python engine/scripts/overlap_check.py --root . && python engine/scripts/verify_manifest.py --root . && python engine/scripts/verify_profiles.py --root . && python engine/scripts/gen_portal_stats.py --check && python engine/scripts/secret_scan.py --root .
```

```bash
python engine/scripts/build.py --refresh-provenance && git diff --stat manifest.json
```

```bash
python engine/scripts/build.py --verify-only
```

针对具体结论的证伪点：

- **F1 的前提**：`curl https://ruleset.skk.moe/List/ip/china_ip.conf | grep -c no-resolve` 应为 0 —— 若非 0，则「引用行是唯一防护点」不成立。
- **F1 的能力假设**：Shadowrocket 的 `RULE-SET,<url>,<policy>,no-resolve` 第 4 字段支持性只有真机证据，无官方文档。若被证伪，回滚成本是一个常量：从 `build_profile.IP_NO_RESOLVE_CLIENTS` 移除 `shadowrocket`、删掉 intent 对应项、重新生成 Profiles（capability 测试会自动跟随）。
- **F2 / F4**：直接构造输入调用 `renderers.render_egern_yaml` / `build_profile.render_client("quantumultx", ...)`，在修复前的提交上应复现异常。
- **F3**：`grep 104.244 Surge/X-ip.conf` 与上游原文对比。
- **F9**：已由 2026-09-12 的每日运行证实（见上）。要复核，在任一次 `Update Rule-Sets` 成功之后跑
  `gh run list --branch main --json name,event,conclusion`，应能看到一条 `Deploy portal to GitHub Pages [workflow_run]`。
- **覆盖盲区**：portal 源码与 `SOURCE_AUDITS.md` 未经审查。在这两处发现的任何问题都不构成对本记录的反驳，而是它明确承认的范围之外。
