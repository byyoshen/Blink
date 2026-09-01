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
| 七端等价性 | `python engine/scripts/parity_check.py --root . --strict` | 四端 classical 逐字节相同；Clash 仅移除 USER-AGENT；Egern/QX 仅移除 PROCESS-NAME；QX 统一省略 no-resolve |
| 产物健康度 | `python engine/scripts/health_check.py --root .` | 非空、合法、无重复、确定性排序、文件头统计正确 |
| 语义多视图一致性 | `python engine/scripts/validate_views.py --root .` | 每个视图（domainset/nonip/ip）种类合法：IP 不进 nonip、domain 不进 ip、纯域名 App 无多余空 ip 视图；Surge 视图内容与 canonical 拆分一致；七端视图文件齐全、头统计（含显式丢弃）正确 |
| 产物溯源 | `python engine/scripts/verify_manifest.py --root .` | 30 App、七端文件、supplement、构建器和 source definition 的 SHA256 完整且一致 |
| Profile 完整性 | `python engine/scripts/verify_profiles.py --root .` | 七端配置可由 intent/templates 逐字节重建；Blink raw 引用存在且非空；语义源与每份产物均保留订阅占位符，App 内订阅适配项显式标注 ADAPTED |
| 跨 App overlap | `python engine/scripts/overlap_check.py --root .` | 相对人工复核基线不得出现新重叠 |
| 敏感模式 | `python engine/scripts/secret_scan.py --root .` | PAT、AWS Key、私钥、代理 URI、URL token/凭据、不透明订阅 URL、正/反斜杠的本地绝对路径 |
| 实时重建 drift | `python engine/scripts/build.py --verify-only --strict-diff` | 重新抓取全部上游并逐字节比对 210 个产物及 provenance |

除最后一项需要实时网络外，其余门禁都能仅凭仓库内容执行。普通 push/PR 运行全部离线门禁；实时 drift 适合发布前、上游审计或人工排障使用，避免把第三方瞬时网络状态变成所有 PR 的随机失败因素。

## `manifest.json`

根目录 `manifest.json` 是生成产物，不手工维护。每次完整 `build.py --write` 会记录：

- `engine/sources/apps.yaml`、`build.py`、`renderers.py` 的 SHA256；
- 本次实际读取的 primary、supplemental 和 v2fly include 文本指纹、字节数、行数；
- 本地 supplement 文件指纹；
- canonical 规则指纹、输入/输出统计、显式 exclude 和 denied include；
- 七个客户端的路径、SHA256、规则数和逐条 dropped 记录。

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

- `checks.yml`：每次 push/PR 运行单测、parity、health、overlap、manifest、Profiles、敏感模式、Python lint、Portal prettier/typecheck 和既有 golden-byte 断言。
- `update.yml`：每日实时抓取、单测、变化阈值、全量写入、全部产物门禁、Portal 数据更新；只有全部成功且产物有变化时才提交。
- 每日构建 JSON 报告以 Actions artifact `build-report` 保存 14 天，不提交运行时报告。
