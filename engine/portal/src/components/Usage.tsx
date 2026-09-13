import { useMemo, useState, type ReactNode } from "react";
import type { ClientKey, PortalData } from "../types";
import { allSnippets, CLIENT_TABS, clientIcon, clientTab } from "../data";
import CodeBlock from "./CodeBlock";
import Reveal from "./Reveal";

const STEPS: Record<ClientKey, ReactNode[]> = {
  surge: [
    <>在 Surge 里添加远程规则（规则集 / 订阅规则页面），粘贴下面的规则链接。</>,
    <>带 IP 的 App 先粘贴域名段链接，再把 IP 段链接放在规则末尾。</>,
    <>客户端按引用自动拉取更新，无需手动改规则文件。</>,
  ],
  shadowrocket: [
    <>在 Shadowrocket 里添加远程规则，粘贴下面的规则链接（一行一个）。</>,
    <>带 IP 的 App 先粘贴域名段链接，再把 IP 段链接放在规则末尾。</>,
    <>客户端按引用自动拉取更新，无需手动改规则文件。</>,
  ],
  loon: [
    <>在 Loon 的远程规则（订阅规则）页面粘贴下面的规则链接（一行一个）。</>,
    <>带 IP 的 App 先粘贴域名段链接，再把 IP 段链接放在规则末尾。</>,
    <>客户端按引用自动拉取更新，无需手动改规则文件。</>,
  ],
  stash: [
    <>
      打开 Stash 配置，把下面整段复制进 <code>rule-providers</code> 与 <code>rules</code>。
    </>,
    <>
      把每个 <code>RULE-SET</code> 行放在 <code>MATCH</code>/<code>FINAL</code> 之前合适的位置；
      分两段的 App，域名段那条要排在 IP 段之前。
    </>,
    <>
      策略名换成你自己的；<code>interval: 86400</code> 控制规则集更新周期。
    </>,
  ],
  mihomo: [
    <>
      打开 mihomo 内核客户端的配置（Clash Meta for Android / FLClash），把下面整段复制进{" "}
      <code>rule-providers</code> 与 <code>rules</code>。
    </>,
    <>
      把每个 <code>RULE-SET</code> 行放在 <code>MATCH</code> 之前合适的位置，域名段排在 IP 段之前；
      规则经 mihomo/ 目录分发（USER-AGENT 已显式去除）。
    </>,
    <>
      策略名换成你自己的；<code>interval: 86400</code> 控制规则集更新周期。
    </>,
  ],
  egern: [
    <>
      在 Egern 的规则里导入下面的规则链接（远程规则 / <code>rule_set</code> 引用）。
    </>,
    <>带 IP 的 App 先导入域名段链接，再把 IP 段链接放在规则末尾。</>,
    <>客户端按引用自动拉取更新，无需手动改规则文件。</>,
  ],
  quantumultx: [
    <>
      在 Quantumult X 的 <code>[filter_remote]</code> 里粘贴下面的规则链接（一行一个）。
    </>,
    <>带 IP 的 App 先粘贴域名段链接，再把 IP 段链接放在规则末尾。</>,
    <>
      行尾 <code>force-policy</code> 换成你自己的策略组，<code>update-interval</code> 控制更新周期。
    </>,
  ],
};

export default function Usage({ data, query }: { data: PortalData; query: string }) {
  const [client, setClient] = useState<ClientKey>("surge");
  const tab = clientTab(client);
  const lines = useMemo(() => allSnippets(data, client, query), [data, client, query]);

  return (
    <section id="usage" className="scroll-mt-24 px-6 py-16 sm:py-20">
      <div className="mx-auto max-w-4xl">
        <Reveal>
          <div className="mx-auto mb-10 max-w-xl text-center">
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">接入你的客户端</h2>
            <p className="mt-2.5 text-mute">
              同一套规则，七种客户端各自的接入方式：非 Mihomo 客户端复制规则链接去前端导入， Stash /
              mihomo 复制配置文件写法。
            </p>
            {query.trim() && (
              <p className="mt-3 inline-block rounded-full border border-accent-soft bg-accent-soft px-3.5 py-1 text-[12.5px] text-accent">
                已按「{query.trim()}」过滤（与规则集搜索联动）
              </p>
            )}
          </div>
        </Reveal>
        <Reveal>
          <div className="mb-6 flex flex-wrap justify-center gap-2.5">
            {CLIENT_TABS.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => setClient(item.key)}
                title={item.badge}
                className={`inline-flex items-center gap-2 rounded-full border px-5 py-2 text-[13.5px] font-medium transition-all duration-200 ease-out active:scale-[0.96] ${
                  client === item.key
                    ? "border-accent bg-accent text-white shadow-sm hover:shadow-md hover:shadow-accent/30"
                    : "border-line bg-card text-mute hover:-translate-y-0.5 hover:border-line-strong hover:text-ink active:translate-y-0"
                }`}
              >
                <img
                  src={clientIcon(item.key)}
                  alt=""
                  width={18}
                  height={18}
                  className="h-[18px] w-[18px] rounded-[5px] object-cover"
                />
                {item.label}
              </button>
            ))}
          </div>
        </Reveal>
        <Reveal>
          <ol className="mx-auto mb-8 flex max-w-4xl flex-wrap justify-center gap-3">
            {STEPS[client].map((step, index) => (
              <li
                key={index}
                className="relative flex-1 basis-56 max-w-80 rounded-2xl border border-line bg-paper py-4 pl-13 pr-4 text-sm"
              >
                <span className="absolute left-4 top-4 flex h-6 w-6 items-center justify-center rounded-full bg-accent text-[13px] font-semibold text-white">
                  {index + 1}
                </span>
                {step}
              </li>
            ))}
          </ol>
        </Reveal>
        <Reveal>
          <div className="mx-auto mb-6 max-w-3xl rounded-2xl border border-accent-soft bg-accent-soft px-5 py-4 text-[13.5px] leading-relaxed">
            <p className="font-semibold text-ink">复制前先看：文件后缀决定引用方式</p>
            <ul className="mt-2 space-y-1.5 text-mute">
              <li>
                <code>-domainset.conf</code>（裸域名清单，如 <code>.example.com</code>）→{" "}
                <code>DOMAIN-SET,&lt;URL&gt;,&lt;策略&gt;,extended-matching</code>
              </li>
              <li>
                <code>-nonip.conf</code> / <code>-ip.conf</code>（带类型的规则行）→{" "}
                <code>RULE-SET,&lt;URL&gt;,&lt;策略&gt;</code>；IP 段末尾再加{" "}
                <code>,no-resolve</code>
              </li>
              <li>
                用错不报错：Surge 只是让规则失效、流量落到 <code>FINAL</code>。分流不对，先查这里。
              </li>
              <li>以 Surge / Shadowrocket 为例；其他客户端照抄页面片段，不要自己改类型。</li>
            </ul>
          </div>
        </Reveal>
        <Reveal>
          <CodeBlock file={tab.fileLabel} copyText={lines} copyLabel="复制全部" maxHeight>
            {lines}
          </CodeBlock>
          <p className="mt-4 text-center text-[13.5px] text-mute">{tab.note}</p>
        </Reveal>
      </div>
    </section>
  );
}
