import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { AppEntry, ClientKey, PortalData } from "../types";
import {
  CATEGORY_LABELS,
  CATEGORY_ORDER,
  CLIENT_TABS,
  VIEW_LABELS,
  VIEW_ORDER,
  appMatchesQuery,
  clientFileUrl,
  clientIcon,
  clientSnippet,
  clientViewSnippet,
  sortedApps,
  sourceLine,
  typeChips,
} from "../data";
import Reveal from "./Reveal";
import { useMediaQuery } from "../hooks";

const MENU_WIDTH = 168;

/* How many cards survive the fold, by how many fit per row.
   The card grid is auto-fill over a 175px minimum, so a phone gets one or two
   columns and a desktop gets four or five. A single limit cannot serve both:
   ten cards is two tidy rows on a desktop and roughly ten screens of scrolling
   on a phone, which buries the next section entirely. */
const COLLAPSED_NARROW = 3;
const COLLAPSED_WIDE = 10;

type CopyOption = {
  label: string;
  detail?: string;
  snippet: string;
};

function CopyRuleButton({ options }: { options: CopyOption[] }) {
  const [open, setOpen] = useState(false);
  const [anchor, setAnchor] = useState<{ top: number; left: number } | null>(null);
  const [copied, setCopied] = useState("");
  const [picked, setPicked] = useState("");
  const triggerRef = useRef<HTMLButtonElement>(null);
  const single = options.length === 1;

  const close = () => {
    setOpen(false);
    setAnchor(null);
  };

  const copy = async (option: CopyOption) => {
    await navigator.clipboard.writeText(option.snippet);
    setCopied(option.label);
    // Keep the menu open briefly so the picked option visibly confirms
    // ("✓ 已复制" highlight) before closing.
    setPicked(option.label);
    window.setTimeout(() => {
      close();
      setPicked("");
    }, 320);
    window.setTimeout(() => setCopied(""), 1200);
  };

  const toggle = () => {
    if (single) {
      copy(options[0]);
      return;
    }
    if (open) {
      close();
      return;
    }
    const rect = triggerRef.current?.getBoundingClientRect();
    const left = Math.max(8, Math.min(rect?.left ?? 8, window.innerWidth - MENU_WIDTH - 8));
    setAnchor({ top: (rect?.bottom ?? 0) + 6, left });
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return;
    const onScroll = () => close();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [open]);

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={toggle}
        className="flex-1 min-w-[80px] rounded-lg bg-accent px-2 py-1.5 text-center text-[13px] font-medium text-white transition-all duration-200 ease-out hover:-translate-y-px hover:bg-accent-strong hover:shadow-md hover:shadow-accent/30 active:scale-95"
      >
        {copied ? "已复制 ✓" : "复制规则链接"}
        {!single && (
          <span
            className={`ml-1 inline-block text-[9px] transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          >
            ▾
          </span>
        )}
      </button>
      {open &&
        anchor &&
        !single &&
        createPortal(
          <>
            {/* Portal to document.body: the menu must escape the card's
                transformed ancestors (Reveal keeps translate-y-0), which
                would otherwise recapture a fixed element and let sibling
                cards cover it. */}
            <div className="fixed inset-0 z-[90]" onClick={close} aria-hidden="true" />
            <div
              className="menu-pop fixed z-[100] rounded-lg border border-line bg-card p-1.5 shadow-lg"
              style={{ top: anchor.top, left: anchor.left, width: MENU_WIDTH }}
              role="menu"
            >
              {options.map((option) => {
                const isPicked = picked === option.label;
                return (
                  <button
                    key={option.label}
                    type="button"
                    onClick={() => copy(option)}
                    className={`group/item flex w-full items-center gap-1.5 rounded-md px-2 py-2 text-left text-[12.5px] transition-all duration-150 ease-out active:scale-[0.97] ${
                      isPicked
                        ? "bg-accent font-semibold text-white"
                        : "text-ink hover:translate-x-0.5 hover:bg-accent-soft hover:text-accent"
                    }`}
                  >
                    <span
                      className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full transition-colors duration-150 ${
                        isPicked ? "bg-white" : "bg-line group-hover/item:bg-accent"
                      }`}
                    />
                    <span className="max-w-[104px] truncate">
                      {isPicked ? "已复制 ✓" : option.label}
                    </span>
                    {option.detail && (
                      <span
                        className={`ml-auto shrink-0 truncate text-[10px] ${
                          isPicked ? "text-white/70" : "text-mute group-hover/item:text-accent/70"
                        }`}
                      >
                        {option.detail}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </>,
          document.body,
        )}
    </>
  );
}

function highlightTag(text: string, query: string) {
  if (!query) return text;
  const index = text.toLowerCase().indexOf(query.toLowerCase());
  if (index === -1) return text;
  return (
    <>
      {text.slice(0, index)}
      <mark className="rounded bg-accent-soft px-0.5 py-0 text-accent">
        {text.slice(index, index + query.length)}
      </mark>
      {text.slice(index + query.length)}
    </>
  );
}

function AppCard({
  app,
  client,
  rawBase,
  query,
  index,
}: {
  app: AppEntry;
  client: ClientKey;
  rawBase: string;
  query: string;
  index: number;
}) {
  const stat = app.clients[client];
  const viewNames = VIEW_ORDER.filter((view) => view in (app.views?.[client] ?? {}));
  const copyOptions: CopyOption[] =
    viewNames.length > 0
      ? viewNames.map((view) => ({
          label: `${VIEW_LABELS[view]}段规则`,
          detail: `${(app.views[client][view].file.split("/").pop() ?? "").replace(/\.conf$/, "")} · ${app.views[client][view].rules} 条`,
          snippet: clientViewSnippet(rawBase, app, client, view),
        }))
      : [{ label: "规则", snippet: clientSnippet(rawBase, app, client) }];
  const dropped =
    client === "egern" || client === "quantumultx" || client === "clash" ? (stat.dropped ?? 0) : 0;
  return (
    <Reveal className="h-full" delay={Math.min(index, 6) * 40}>
      <article
        title={app.note || app.name}
        className="flex h-full flex-col gap-2.5 rounded-2xl border border-line bg-card p-3.5 transition duration-200 hover:-translate-y-0.5 hover:border-line-strong hover:shadow-lg"
      >
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-line bg-paper">
            {app.icon ? (
              <img
                src={app.icon}
                alt=""
                width={32}
                height={32}
                className="h-full w-full object-cover"
              />
            ) : (
              <span className="text-base">{app.emoji}</span>
            )}
          </span>
          <div className="min-w-0 leading-tight">
            <div className="truncate text-sm font-semibold tracking-tight">
              {highlightTag(app.name, query)}
            </div>
            <div className="truncate text-[11px] text-mute">
              {highlightTag(CATEGORY_LABELS[app.category] ?? app.category, query)}
            </div>
          </div>
        </div>
        <div className="flex items-baseline gap-1">
          <strong className="text-xl font-bold tracking-tight text-accent">{stat.rules}</strong>
          <span className="text-[11px] text-mute">条规则</span>
        </div>
        <div className="flex flex-wrap gap-1">
          {typeChips(app, client).map((chip) => (
            <span
              key={chip.label}
              className="rounded-full border border-line bg-paper px-1.5 py-0.5 text-[11px] text-mute"
            >
              {chip.label} <b className="font-semibold text-ink">{chip.count}</b>
            </span>
          ))}
        </div>
        {viewNames.length > 1 && (
          <p className="rounded-lg border border-accent-soft bg-accent-soft px-1.5 py-1 text-[10px] text-accent">
            域名 + IP 两段
          </p>
        )}
        {app.self_use && (
          <p className="rounded-lg border border-accent-soft bg-accent-soft px-1.5 py-1 text-[10px] leading-relaxed text-accent">
            ⚠️ 个人维护的直播源 · 请按自身直播源自行配置
          </p>
        )}
        {dropped > 0 && (
          <p className="rounded-lg border border-line bg-paper px-1.5 py-1 text-[10px] leading-relaxed text-mute">
            ⚠️ {dropped} 条 {client === "clash" ? "USER-AGENT" : "PROCESS-NAME"} 无法在{" "}
            {client === "egern" ? "Egern" : client === "clash" ? "Clash" : "Quantumult X"}{" "}
            无损表达， 构建器已显式丢弃。
          </p>
        )}
        <p className="truncate text-[11px] text-mute" title={app.source.name || undefined}>
          {sourceLine(app)}
        </p>
        <div className="mt-auto flex flex-wrap items-center gap-1.5 pt-0.5">
          <CopyRuleButton options={copyOptions} />
          <a
            href={clientFileUrl(rawBase, app, client)}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex-1 min-w-[80px] rounded-lg border border-line bg-card px-2 py-1.5 text-center text-[13px] font-medium text-ink transition-all duration-200 ease-out hover:-translate-y-0.5 hover:bg-paper active:translate-y-0 active:scale-[0.96]"
          >
            查看{" "}
            <span className="inline-block transition-transform duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5">
              ↗
            </span>
          </a>
        </div>
      </article>
    </Reveal>
  );
}

export default function Rulesets({
  data,
  query,
  onQueryChange,
}: {
  data: PortalData;
  query: string;
  onQueryChange: (value: string) => void;
}) {
  const [client, setClient] = useState<ClientKey>("surge");
  const [filter, setFilter] = useState("all");
  const [expanded, setExpanded] = useState(false);
  const wide = useMediaQuery("(min-width: 640px)");
  const gridRef = useRef<HTMLDivElement>(null);
  const apps = useMemo(() => sortedApps(data.apps), [data.apps]);
  const present = useMemo(() => new Set(apps.map((app) => app.category)), [apps]);
  const filters = ["all", ...CATEGORY_ORDER.filter((category) => present.has(category))];
  const categoryApps = filter === "all" ? apps : apps.filter((app) => app.category === filter);
  const results = categoryApps.filter((app) => appMatchesQuery(app, query));
  const activeNote = CLIENT_TABS.find((tab) => tab.key === client)?.note ?? "";
  const collapsedCount = wide ? COLLAPSED_WIDE : COLLAPSED_NARROW;
  const shown = expanded ? results : results.slice(0, collapsedCount);
  const collapsible = results.length > collapsedCount;

  const toggleExpanded = () => {
    // Collapsing deletes every row above the button, so whatever sits at the
    // reader's scroll offset afterwards is no longer what they were reading --
    // on a phone the drop is long enough to land them in the next section.
    // Put the top of the grid back in view instead. No explicit behavior, so
    // the CSS scroll-behavior governs and the reduced-motion override in
    // index.css still applies.
    if (expanded) {
      requestAnimationFrame(() => gridRef.current?.scrollIntoView({ block: "start" }));
    }
    setExpanded(!expanded);
  };

  return (
    <section
      id="rulesets"
      className="scroll-mt-24 border-y border-line bg-paper px-6 py-16 sm:py-20"
    >
      <div className="mx-auto max-w-5xl">
        <Reveal>
          <div className="mx-auto mb-8 max-w-xl text-center">
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">规则集</h2>
            <p className="mt-2.5 text-mute">
              全部由构建器生成，绝不手工维护；范围优先于数量，不为覆盖而吞入无关 CDN。
            </p>
          </div>
        </Reveal>
        <Reveal>
          <div className="mx-auto mb-8 max-w-3xl rounded-2xl border border-line bg-card p-4 text-[13px] leading-relaxed text-mute">
            <p className="mb-2 font-semibold text-ink">规则怎么用，看 App 而定</p>
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="rounded-xl border border-line bg-paper p-3">
                <p className="font-medium text-ink">只有域名规则</p>
                <p className="mt-0.5">多数 App 只有域名规则，直接点「复制规则链接」导入即可。</p>
              </div>
              <div className="rounded-xl border border-line bg-paper p-3">
                <p className="font-medium text-ink">域名 + IP</p>
                <p className="mt-0.5">
                  部分 App（如 Netflix / X / Telegram）分「域名段」「IP 段」两块，点「复制规则链接」
                  会弹出两个选项，分别复制这两段。
                </p>
              </div>
            </div>
            <p className="mt-3 border-t border-line pt-2">
              导出方式：非 mihomo 复制的是规则链接，去客户端前端导入；Stash / Clash 复制的是
              配置文件写法（rule-providers + RULE-SET），需写进配置。
            </p>
          </div>
        </Reveal>
        <Reveal>
          <div className="mb-4 flex justify-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-accent-soft bg-accent-soft px-5 py-2 text-[13.5px] font-bold tracking-wide text-accent shadow-sm">
              <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
              先选择你要导入的客户端，再复制规则链接
            </span>
          </div>
          <div className="mb-4 flex flex-wrap justify-center gap-2.5">
            {CLIENT_TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setClient(tab.key)}
                title={tab.badge}
                className={`inline-flex items-center gap-2 rounded-full border px-5 py-2 text-[13.5px] font-medium transition-all duration-200 ease-out active:scale-[0.96] ${
                  client === tab.key
                    ? "border-accent bg-accent text-white shadow-sm hover:shadow-md hover:shadow-accent/30"
                    : "border-line bg-card text-mute hover:-translate-y-0.5 hover:border-line-strong hover:text-ink active:translate-y-0"
                }`}
              >
                <img
                  src={clientIcon(tab.key)}
                  alt=""
                  width={18}
                  height={18}
                  className="h-[18px] w-[18px] rounded-[5px] object-cover"
                />
                {tab.label}
              </button>
            ))}
          </div>
          <p className="mx-auto mb-7 max-w-2xl text-center text-[13px] text-mute">{activeNote}</p>
        </Reveal>
        <Reveal>
          <div className="relative mx-auto mb-6 max-w-md">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-mute transition-colors duration-200 peer-focus:text-accent"
            >
              <circle cx="11" cy="11" r="7" />
              <path d="m21 21-4.3-4.3" />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="搜索 App，如 YouTube / Netflix / Telegram…"
              aria-label="搜索 App 规则"
              className="peer w-full rounded-full border border-line bg-card py-2.5 pl-11 pr-10 text-sm text-ink shadow-sm outline-none transition-all duration-200 ease-out placeholder:text-mute/70 focus:-translate-y-px focus:border-accent focus:bg-paper focus:shadow-md focus:shadow-accent/15 focus:ring-2 focus:ring-accent/15"
            />
            {query && (
              <button
                type="button"
                onClick={() => onQueryChange("")}
                aria-label="清空搜索"
                className="absolute right-3 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full text-mute transition-all duration-150 ease-out hover:bg-paper hover:text-ink active:scale-90"
              >
                ✕
              </button>
            )}
          </div>
          {query.trim() && (
            <p className="mx-auto -mt-2 mb-5 text-center text-[12px] text-mute">
              共找到 <b className="text-ink">{results.length}</b> 个匹配 App
            </p>
          )}
        </Reveal>
        <div className="mb-7 flex flex-wrap justify-center gap-2">
          {filters.map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => setFilter(key)}
              className={`rounded-full border px-4 py-1.5 text-[13.5px] transition-all duration-200 ease-out hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.95] ${
                filter === key
                  ? "border-accent bg-accent text-white shadow-sm"
                  : "border-line bg-card text-mute hover:border-line-strong hover:text-ink"
              }`}
            >
              {key === "all" ? "全部" : CATEGORY_LABELS[key]}
            </button>
          ))}
        </div>
        {results.length === 0 ? (
          <div className="rounded-2xl border border-line bg-card px-6 py-14 text-center">
            <p className="text-2xl">🔍</p>
            <p className="mt-3 font-medium text-ink">没有匹配的 App</p>
            <p className="mt-1 text-[13px] text-mute">
              把关键词换成 App 名称（如 Netflix）或分类（如 社交 / 媒体 / AI）再试。
            </p>
            <button
              type="button"
              onClick={() => {
                onQueryChange("");
                setFilter("all");
              }}
              className="mt-5 rounded-full border border-accent-soft bg-accent-soft px-4 py-2 text-[13px] font-medium text-accent transition-all duration-200 ease-out hover:-translate-y-0.5 hover:shadow-md hover:shadow-accent/20 active:translate-y-0 active:scale-[0.96]"
            >
              清除搜索与分类
            </button>
          </div>
        ) : (
          <div
            ref={gridRef}
            className="grid scroll-mt-24 grid-cols-[repeat(auto-fill,minmax(175px,1fr))] gap-3"
          >
            {shown.map((app, index) => (
              <AppCard
                key={app.name}
                app={app}
                client={client}
                rawBase={data.raw_base}
                query={query}
                index={index}
              />
            ))}
          </div>
        )}
        {collapsible && (
          <div className="mt-7 flex justify-center">
            <button
              type="button"
              onClick={toggleExpanded}
              className="inline-flex items-center gap-2 rounded-full border border-line bg-card px-6 py-2.5 text-sm text-ink transition-all duration-200 ease-out hover:-translate-y-0.5 hover:border-line-strong hover:shadow-sm active:translate-y-0 active:scale-[0.96]"
            >
              {expanded ? "收起" : `展开全部 ${results.length} 个 App`}
              <span
                className={`inline-block text-xs transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
              >
                ▾
              </span>
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
