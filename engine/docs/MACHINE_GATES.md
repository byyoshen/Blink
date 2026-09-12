# Blink 机器门禁

## 目标与事实来源

本文件记录 2026-08-18 起启用的产物正确性、可追溯性和供应链变化门禁。规则语义与客户端降级事实仍以 `AGENTS.md` 和 `MULTI_CLIENT_AUDIT.md` 为准；本文件只说明这些承诺如何被机器执行。

门禁遵守以下边界：

- 不提交上游规则正文缓存；每日发布构建仍实时读取上游。
- 上游不可用时构建失败且不写产物，仓库内上一版规则继续可用；不以陈旧缓存静默生成。
- `manifest.json` 不含时间戳、commit、本地路径或其他运行环境信息，只保存确定性的内容指纹和统计。
- `Profiles/` 仍为人工演进层，不进入每日 `update.yml` 写入范围；push/PR 只校验其可复现性和引用完整性。

## 门禁清单

| 门禁 | 命令 | 强制内容 |
| --- | --- | --- |
| 单元与回归 | `python -m unittest discover -s engine/tests -v` | Parser、renderer、Profile、变化阈值和故障注入 |
| 七端等价性 | `python engine/scripts/parity_check.py --root .` | 四端 classical 逐字节相同；Clash 仅移除 USER-AGENT；Egern/QX 仅移除 PROCESS-NAME；QX 统一省略 no-resolve |
| 产物健康度 | `python engine/scripts/health_check.py --root .` | 非空、合法、无重复、确定性排序、文件头统计正确 |
| 语义多视图一致性 | `python engine/scripts/validate_views.py --root .` | 每个视图（domainset/nonip/ip）种类合法：IP 不进 nonip、domain 不进 ip、纯域名 App 无多余空 ip 视图；Surge 视图内容与 canonical 拆分一致；七端视图文件齐全、头统计（含显式丢弃）正确 |
| 产物溯源 | `python engine/scripts/verify_manifest.py --root .` | 30 App、七端文件、supplement、构建器和 source definition 的 SHA256 完整且一致 |
| Profile 完整性 | `python engine/scripts/verify_profiles.py --root .` | 七端配置可由 intent/templates 逐字节重建；Blink raw 引用存在且非空；语义源与每份产物均保留订阅占位符，App 内订阅适配项显式标注 ADAPTED |
| 跨 App overlap | `python engine/scripts/overlap_check.py --root .` | 相对人工复核基线不得出现新重叠 |
| Portal 数据同步 | `python engine/scripts/gen_portal_stats.py --check` | `engine/portal/public/data/stats.json` 与当前七端产物逐字节一致（定向 `--app` 写入后忘记重算会被拦住） |
| 敏感模式 | `python engine/scripts/secret_scan.py --root .` | PAT、AWS Key、私钥、代理 URI、URL token/凭据、不透明订阅 URL、正/反斜杠的本地绝对路径 |
| 实时重建 drift | `python engine/scripts/build.py --verify-only` | 重新抓取全部上游并逐字节比对 210 个产物及 provenance |

> 改动 `build.py` / `renderers.py` 后，若确认输出未变，用离线的 `build.py --refresh-provenance` 重建 `manifest.json`（见下文），不要为此跑实时 `--write`。

除最后一项需要实时网络外，其余门禁都能仅凭仓库内容执行。普通 push/PR 运行全部离线门禁；实时 drift 适合发布前、上游审计或人工排障使用，避免把第三方瞬时网络状态变成所有 PR 的随机失败因素。

## `manifest.json`

根目录 `manifest.json` 是生成产物，不手工维护。每次完整 `build.py --write` 会记录：

- `engine/sources/apps.yaml`、`build.py`、`renderers.py` 的 SHA256；
- 本次实际读取的 primary、supplemental 和 v2fly include 文本指纹、字节数、行数；
- 本地 supplement 文件指纹；
- canonical 规则指纹、输入/输出统计、显式 exclude 和 denied include；
- `canonical.excluded_domains`：每条已声明 domain exclude 的命中数（仅声明了 domain exclude 的 App 才有该字段）。type-level exclude 一直记在 `skipped_excluded`，domain 级此前完全无痕，无法从 `input_rules → rules` 的差值区分"被 exclude"与"被去重"。记命中数后，某条 exclude 因上游改写而**静默失效**会变成每日提交里可见的 `1 → 0` diff；`build.py` 同时在 stderr 打印一条 warning，但不中断构建（上游合法移除该规则时不应自锁每日管线）。
- 七个客户端的路径、SHA256、规则数和逐条 dropped 记录。

构建报告（非提交产物）另记 `rewritten_ip_rules`：IP 规则被规范化时的 `before -> after`。`ipaddress.ip_network(strict=False)` 会把 `IP-CIDR,1.2.3.4/24` 读成 `1.2.3.0/24`、把裸地址补成 `/32` —— 两者都是标准 CIDR 解读，但前者**放宽了上游作者实际写下的范围**，属于"禁止静默转换"覆盖的情形，因此逐条记入报告并在 stderr 提示。不中断构建：上游写法不规范不应阻断每日更新，且规范化后的结果本来就会出现在产物 diff 里。

## 纯 provenance 刷新（`--refresh-provenance`）

`manifest.json` 记录 `build.py` / `renderers.py` 的 SHA256，所以**改动构建器本身**（哪怕只加一行注释）就会让 `verify_manifest.py` 失败。用实时 `--write` 重建会把当天的上游内容变化一起拖进一个本该只含代码的提交里，于是提供离线模式：

```text
python engine/scripts/build.py --refresh-provenance
```

- 重算一切可从**已提交产物**派生的指纹：builder / source definition 指纹、canonical 指纹与规则数、七端产物 SHA256 与 dropped、语义视图记录。
- 只有实时抓取才能确立的事实从现有 manifest **原样继承**：上游文本指纹与字节/行数、`input_rules`、`skipped_attributes`、`skipped_excluded`、`denied_includes`、`excluded_domains`。
- 它只对"不改变任何输出"的改动有效，并且会自己证明这一点：已提交的七端产物与视图必须仍能从已提交的 canonical 规则逐字节重新渲染出来，且 `apps.yaml` 声明的上游集合必须仍与 manifest 记录的一致。任一条不成立就拒绝执行并要求跑真正的 `--write`（新增 App、换源、renderer 行为变化都属于这一类）。
- 它**不能**替代 `--write`：上游内容变化只能由实时构建记录。

## 过期产物清理

`build.py --write` 会在写入后删除当前语义拆分不再产出的 view 文件（`semantic_views()` 会省略空视图，所以某 App 上游失去最后一条 IP 规则、或 `nonip` 因 keyword 消失而变成 `domainset` 时会留下孤儿文件，`validate_views.py` 判为 spurious，此后每日构建都会失败直到有人手工删除）。只处理七个客户端目录下 `<App>-<view>.conf` 这一确定命名、且只针对本次构建的 App；删除项记入构建报告的 `pruned_views`，绝不静默。已禁用 App 留下的主产物仍由 `parity_check` 的 file-set 断言报出（错误信息已足够可操作），不在自动清理范围内。

不在 manifest 中写抓取时间或 commit，是为了保证同一输入得到逐字节相同的 manifest。上游身份由 HTTPS URL 和内容指纹共同确定。

## 上游变化门禁

`build.py --write` 在任何写入前，将实时编译后的 canonical 规则与已提交 `Surge/*.list` 做集合比较。默认阻断条件为任一项成立：

- 新增或删除规则数超过 20；
- 对旧集合的语义变化比例超过 20%；
- 出现此前不存在的规则类型。

失败报告包含 `+N/-N`、变化比例、新类型和最多五条增删样例。确认来源、范围和格式风险均可接受后，维护者才可显式运行：

```text
python engine/scripts/build.py --write --accept-large-change
```

该参数不关闭解析、renderer、parity、health 或 checksum 校验，只跳过已经人工审阅的变化量阈值。

## 当前 overlap 基线

`engine/reports/overlap_baseline.json` 固化四组已知交集：AI×X（Grok）、Facebook×Instagram、Facebook×WhatsApp、Google×YouTube，共 21 条。新交集会阻断 CI；确认无害后使用下面的显式命令更新基线：

```text
python engine/scripts/overlap_check.py --root . --write-baseline
```

## CI 执行位置

- `checks.yml`：每次 push/PR 运行单测、parity、health、validate_views、overlap、manifest、Portal 数据同步、Profiles、敏感模式、Python lint、Portal prettier/typecheck 和既有 golden-byte 断言。
- `update.yml`：每日实时抓取、单测、变化阈值、全量写入、全部产物门禁、Portal 数据更新；只有全部成功且产物有变化时才提交。
- `pages.yml`：portal 源码 push 时部署，并在 `Update Rule-Sets` 成功完成后通过 `workflow_run` 再部署一次 —— 每日提交由默认 `GITHUB_TOKEN` 产生，这类 push 不会触发其他 workflow，少了这个触发器门户上的规则数会停留在上一次人工 portal 提交。
- 每日构建 JSON 报告以 Actions artifact `build-report` 保存 14 天，不提交运行时报告。

## 仓库身份一致性

`engine/scripts/repo_identity.py` 是 owner/repo slug 的唯一来源，全部生成引用由它派生；`engine/tests/test_repo_identity.py` 另外扫描 README、门户外壳、设计文档与 `Profiles/`（当前 88 处自引用），任何指向本仓库却使用了旧 owner 的 URL 都会失败。改名只需改该模块 + 手写文档，漏改会被测试点名而不是变成一个看起来正常的 404。该扫描同时断言匹配数不得低于下限，避免正则失效后"什么都不校验"地通过 —— 与 `verify_profiles` 的 raw URL 正则同一个教训。

## 行尾与字节级门禁

`manifest.json` 记录的是**字节** SHA256，`verify_manifest.py` 与 `build.py --verify-only` 按字节比较。仓库根的 `.gitattributes` 把全部文本文件固定为 `eol=lf`：

- Windows 上 `core.autocrlf=true` 的 checkout 不会再产出 CRLF 工作区，维护者本地可以直接跑 provenance 门禁；
- CRLF 永远进不了提交。否则 CI 只有 `verify_manifest` 会红，而按文本读取的 `parity_check` 与 golden-byte 仍然是绿的，排查方向会被误导。
