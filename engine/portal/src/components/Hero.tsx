import CodeBlock from "./CodeBlock";

interface HeroProps {
  appsCount: number;
  totalRules: number;
  /** Raw base from stats.json, so the example line cannot drift from the real URLs. */
  rawBase: string;
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <li className="flex flex-col gap-0.5 rounded-2xl border border-line bg-paper px-5 py-4 sm:max-w-52 sm:flex-1">
      <strong className="text-lg font-bold tracking-tight">{value}</strong>
      <span className="text-[13px] text-mute">{label}</span>
    </li>
  );
}

export default function Hero({ appsCount, totalRules, rawBase }: HeroProps) {
  const exampleUrl = `${rawBase}/Surge/YouTube.list`;
  const exampleLine = `RULE-SET,${exampleUrl},Proxy`;
  return (
    <section id="top" className="hero-bg px-6 pb-16 pt-24 text-center sm:pt-28">
      <p
        className="hero-enter mx-auto mb-5 inline-block rounded-full border border-accent-soft bg-accent-soft px-3.5 py-1 text-[13px] font-semibold tracking-wide text-accent"
        style={{ animationDelay: "0ms" }}
      >
        多客户端规则与配置 · 自动构建 · 稳定分发
      </p>
      <h1
        className="hero-enter mx-auto max-w-3xl text-[clamp(2rem,5.2vw,3.25rem)] font-bold leading-[1.2] tracking-tight"
        style={{ animationDelay: "70ms" }}
      >
        一次审计
        <br className="hidden sm:block" />
        <span className="bg-gradient-to-r from-accent to-[#8b5cf6] bg-clip-text text-transparent">
          多端适用
        </span>
      </h1>
      <p
        className="hero-enter mx-auto mt-5 max-w-xl text-base text-mute"
        style={{ animationDelay: "140ms" }}
      >
        每日从可信上游保守转换 App 专用规则，渲染为七种客户端格式；同一份配置意图另迁移为七客户端
        配置文件，单订阅池、占位符内置，替换一条订阅即可复用。规则自动更新，配置人工维护、
        真机验证后发布。
      </p>
      <div
        className="hero-enter mt-7 flex justify-center gap-3"
        style={{ animationDelay: "210ms" }}
      >
        <span className="rotating-border inline-block rounded-full p-[1.5px]">
          <a
            href="#usage"
            className="inline-block rounded-full bg-accent px-6 py-2.5 text-[15px] font-medium text-white transition-all duration-200 ease-out hover:-translate-y-0.5 hover:bg-accent-strong hover:shadow-lg hover:shadow-accent/30 active:translate-y-0 active:scale-[0.96]"
          >
            开始使用
          </a>
        </span>
        <a
          href="#rulesets"
          className="rounded-full border border-line bg-card px-6 py-2.5 text-[15px] font-medium text-ink transition-all duration-200 ease-out hover:-translate-y-0.5 hover:border-line-strong hover:bg-paper hover:shadow-md active:translate-y-0 active:scale-[0.96]"
        >
          查看规则集
        </a>
      </div>
      <div className="hero-enter mx-auto mt-11 max-w-2xl" style={{ animationDelay: "280ms" }}>
        <CodeBlock file="Surge 主配置 · [Rule]" copyText={exampleLine}>
          <span className="text-white/40"># 一行接入，策略名由你自己决定{"\n"}</span>
          <span className="text-[#8ab4ff]">RULE-SET</span>
          {`,${exampleUrl},`}
          <span className="text-[#7ee2a8]">Proxy</span>
        </CodeBlock>
      </div>
      <ul
        className="hero-enter mx-auto mt-10 grid max-w-3xl grid-cols-2 gap-3 sm:flex sm:flex-wrap sm:justify-center"
        style={{ animationDelay: "350ms" }}
      >
        <Stat value={String(appsCount)} label="规则集" />
        <Stat value={String(totalRules)} label="有效规则" />
        <Stat
          value="7 客户端"
          label="Surge · Shadowrocket · Loon · Stash · mihomo · Egern · Quantumult X"
        />
        <Stat value="7 配置文件" label="完整可导入 · 单订阅池 · 占位符内置" />
        <Stat value="每日 00:01" label="规则自动检查上游" />
        <Stat value="审计准入" label="证据优先 · 每 App 独立审计" />
      </ul>
    </section>
  );
}
