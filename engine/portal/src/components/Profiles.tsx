import { useState } from "react";
import type { ClientKey, PortalData } from "../types";
import {
  CLIENT_TABS,
  PROFILE_FILES,
  clientIcon,
  profileFileUrl,
  profileInstallScheme,
} from "../data";
import { useCopy } from "../hooks";
import Reveal from "./Reveal";

const STEPS = [
  <>下载对应客户端的配置文件。</>,
  <>
    用文本编辑器把 <code>https://YOUR-SUBSCRIPTION-URL</code> 替换成你的订阅链接。
  </>,
  <>导入客户端并真机验证策略组与分流效果。</>,
];

export default function Profiles({ data }: { data: PortalData }) {
  const [client, setClient] = useState<ClientKey>("surge");
  const url = profileFileUrl(data.raw_base, client);
  const scheme = profileInstallScheme(data.raw_base, client);
  const { state, copy } = useCopy(url);
  const tab = CLIENT_TABS.find((item) => item.key === client);

  return (
    <section id="profiles" className="scroll-mt-24 px-6 py-16 sm:py-20">
      <div className="mx-auto max-w-4xl">
        <Reveal>
          <div className="mx-auto mb-8 max-w-xl text-center">
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">配置文件</h2>
            <p className="mt-2.5 text-mute">
              按普适性维护的推荐配置模板，真机验证后发布；人工维护、不随规则每日更新。
            </p>
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
          <div className="mx-auto max-w-2xl rounded-2xl border border-line bg-card p-6">
            <div className="flex flex-wrap items-center gap-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-line bg-paper">
                <img
                  src={clientIcon(client)}
                  alt=""
                  width={44}
                  height={44}
                  className="h-full w-full object-cover"
                />
              </span>
              <div className="leading-tight">
                <div className="font-semibold tracking-tight">{tab?.label} 配置文件</div>
                <div className="text-xs text-mute">
                  {PROFILE_FILES[client].kind} · 单订阅池 · 占位符已内置
                </div>
              </div>
              <div className="ml-auto flex flex-wrap justify-end gap-2">
                {scheme && (
                  <a
                    href={scheme}
                    className="rounded-full border border-accent-soft bg-accent-soft px-4 py-2 text-sm font-medium text-accent transition-all duration-200 ease-out hover:-translate-y-0.5 hover:shadow-md hover:shadow-accent/20 active:translate-y-0 active:scale-[0.96]"
                  >
                    iOS 一键导入
                  </a>
                )}
                <button
                  type="button"
                  onClick={copy}
                  className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition-all duration-200 ease-out hover:bg-accent-strong hover:shadow-md hover:shadow-accent/30 active:scale-[0.96]"
                >
                  {state === "done" ? "已复制链接 ✓" : state === "failed" ? "复制失败" : "复制链接"}
                </button>
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-full border border-line bg-card px-4 py-2 text-sm text-ink transition-all duration-200 ease-out hover:-translate-y-0.5 hover:bg-paper active:translate-y-0 active:scale-[0.96]"
                >
                  下载 ↗
                </a>
              </div>
            </div>
            <ol className="mt-5 space-y-2 border-t border-line pt-4">
              {STEPS.map((step, index) => (
                <li key={index} className="flex items-start gap-2.5 text-sm text-mute">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent text-[11px] font-semibold text-white">
                    {index + 1}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
            <p className="mt-4 text-[13px] leading-relaxed text-mute">
              配置以单一订阅池组织：所有策略组与地区筛选只依赖一条订阅，替换后即可复用；
              规则全部通过远程 URL 引用（Blink 规则 + 成熟上游基础设施），不复制规则内容。
            </p>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
