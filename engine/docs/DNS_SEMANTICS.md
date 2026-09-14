# Blink 规则模型的 DNS 语义与顺序不变式

> 本文是「域名段必须置于 IP 段之前」这条不变式的唯一依据：它为什么成立、违反后
> 会发生什么、以及哪道门禁在守它。
>
> 这里不写客户端格式事实（以 `MULTI_CLIENT_AUDIT.md` 为准），也不写门禁的完整
> 清单（以 `MACHINE_GATES.md` 为准），只解释规则模型本身的形状。

## 规则类型即 DNS 语义

代理客户端匹配 **IP 规则**时必须先知道目标 IP —— 也就是必须先把域名解析掉。因此
「这条规则会不会触发本地 DNS 解析」取决于它匹配的是域名还是 IP，而 canonical 规则
类型已经把这件事写在了名字里。`build.py` 的 `semantic_views()` 正是从这一点派生出
语义分段视图：

| 规则类型 | 匹配是否需要本地解析 | 所属分段 |
| --- | --- | --- |
| `DOMAIN` / `DOMAIN-SUFFIX` / `DOMAIN-KEYWORD` | 否 | 非 IP 段 |
| `USER-AGENT` / `PROCESS-NAME` | 否 | 非 IP 段 |
| `IP-CIDR` / `IP-CIDR6` | **是** | IP 段 |

「非 IP 段」是一个视图，但它的**文件名叫什么**取决于内容：整段只有 `DOMAIN` /
`DOMAIN-SUFFIX` 时产出 `-domainset.conf`（裸域名清单），只要出现 `DOMAIN-KEYWORD` /
`USER-AGENT` / `PROCESS-NAME` 就改为产出 `-nonip.conf`（classical 规则行）。两者互斥，
同一 App 只会得到其中之一 —— 权威定义见 `engine/scripts/validate_views.py` 的
`VIEW_KINDS`。

只有走到 IP 段、`FINAL` 或直连时，解析才应该发生。域名段命中即终止匹配，解析根本
不会发生 —— 这就是 DNS 防污染保护的来源。

## 不变式

**所有域名段必须置于所有 IP 段之前，没有例外。**

顺序一旦反过来，一个本该走代理的域名会先被客户端解析成 IP，再拿去匹配 IP 规则；这个
解析请求走的是本地 DNS，正是防污染要避免的暴露。

对应实现：

- `build.py` 的 `semantic_views()` 按「非 IP 段在前、IP 段在后」返回视图，`phase_of()`
  给出每条规则的分段；
- `engine/scripts/validate_views.py` 断言每个视图的种类合法（IP 不进 `nonip`、domain 不进
  `ip`、纯域名 App 不产出空 `ip` 视图），并核对七端视图文件齐全与文件头统计正确。

## 违反后的表现：静默失效

顺序或引用类型写反时 **Surge 不报错**：该规则集只是不生效，流量悄悄落到 `FINAL`。

这是本仓库把不变式写进门禁、而不是留给读者自觉的唯一理由 —— 唯一的可观测信号是
「分流结果与预期不符」，而它与「上游漏了这条规则」看起来完全一样。

同一类静默失效在引用类型上也会发生：`-domainset.conf` 必须用 `DOMAIN-SET` 引用，
`-nonip.conf` / `-ip.conf` 必须用 `RULE-SET` 引用，写反同样不报错。文件后缀就是答案。

## 来源与沿革

这个分类与不变式来自 SukkaW 的 Surge 配置方法论，以及本仓库对其生产文件的核对：

- [SukkaW/Surge](https://github.com/SukkaW/Surge)
- [I have my unique Surge setup](https://blog.skk.moe/post/i-have-my-unique-surge-setup/)
- [DNS 泄漏、CDN 访问优化与 Fake IP](https://blog.skk.moe/post/lets-talk-about-dns-cdn-fake-ip/)
- [生活在字典树上](https://blog.skk.moe/post/how-to-store-way-too-many-domains-and-ips-101/)

domainset / non_ip / ip 三拆分在本仓库的落地沿革见 `MULTI_CLIENT_AUDIT.md` §8 与 §12。
