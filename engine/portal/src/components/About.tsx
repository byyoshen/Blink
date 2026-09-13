import Reveal from "./Reveal";

interface AboutProps {
  repo: string;
}

/* These two were the only unstyled anchors in the portal, so they fell back to
   the browser default -- which in dark mode is a near-unreadable blue. */
const DOC_LINK = "text-accent underline underline-offset-2 hover:text-accent-strong";

const PIPELINE = [
  { title: "Source audit", text: "每个 App 记录候选、证据与结论" },
  { title: "build.py", text: "解析 / 转换 / 规范化 / 去重，异常即中止" },
  { title: "supplement", text: "只合并经 Surge 日志证实的上游缺口" },
  {
    title: "语义拆分",
    text: "domainset / nonip / ip 三段视图（IP 段恒在后），域名类规则不提前触发 DNS",
  },
  {
    title: "多客户端渲染",
    text: "classical ×4 + mihomo 变体（去 UA）+ Egern YAML + QX filter；无法表达的类型显式丢弃并计数",
  },
  { title: "配置迁移", text: "Canonical Profile Intent → 七客户端配置文件，人工审核 + 真机验证" },
  { title: "稳定 raw URL", text: "规则每日自动更新；配置人工维护后发布" },
];

export default function About({ repo }: AboutProps) {
  return (
    <section id="about" className="scroll-mt-24 px-6 py-16 sm:py-20">
      <div className="mx-auto max-w-5xl">
        <Reveal>
          <div className="mx-auto mb-10 max-w-xl text-center">
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">构建与来源</h2>
            <p className="mt-2.5 text-mute">
              每个 App 先审计、后转换；构建显式失败，而不是静默改变规则语义。
            </p>
          </div>
        </Reveal>
        <div className="grid gap-4 md:grid-cols-2">
          <Reveal className="h-full">
            <div className="h-full rounded-2xl border border-line bg-paper p-6">
              <h3 className="mb-4 text-base font-bold">构建管线</h3>
              <ol className="flex flex-wrap items-stretch gap-2">
                {PIPELINE.map((step, index) => (
                  <li
                    key={step.title}
                    className="flex flex-1 basis-40 flex-col gap-1 rounded-xl border border-line bg-card p-3"
                  >
                    <span className="text-[11px] font-semibold tracking-wide text-accent">
                      STEP {index + 1}
                    </span>
                    <strong className="text-sm font-semibold">{step.title}</strong>
                    <span className="text-xs leading-relaxed text-mute">{step.text}</span>
                  </li>
                ))}
              </ol>
            </div>
          </Reveal>
          <Reveal className="h-full">
            <div className="h-full rounded-2xl border border-line bg-paper p-6">
              <h3 className="mb-4 text-base font-bold">来源原则</h3>
              <ul className="space-y-3">
                <li className="relative pl-5 text-sm">
                  <span className="absolute left-0 top-2 h-1.5 w-1.5 rounded-[2px] bg-accent" />
                  每个 App
                  独立审计选源：以更新活跃度、覆盖、范围、格式与维护质量为证据，作者偏好只作并列时的
                  tie-breaker。
                </li>
                <li className="relative pl-5 text-sm">
                  <span className="absolute left-0 top-2 h-1.5 w-1.5 rounded-[2px] bg-accent" />
                  每个 App 默认 1 个主源、最多 1 个补充源；补充规则只收录经 Surge 日志确认的缺口。
                </li>
                <li className="relative pl-5 text-sm">
                  <span className="absolute left-0 top-2 h-1.5 w-1.5 rounded-[2px] bg-accent" />
                  Reject / 国内分流 / CDN / LAN 等基础设施不纳入，继续直接引用成熟上游。
                </li>
                <li className="relative pl-5 text-sm">
                  <span className="absolute left-0 top-2 h-1.5 w-1.5 rounded-[2px] bg-accent" />
                  生成产物不附统一许可证，使用前请查看{" "}
                  <a
                    href={`${repo}/blob/main/THIRD_PARTY_NOTICES.md`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={DOC_LINK}
                  >
                    第三方声明
                  </a>{" "}
                  与{" "}
                  <a
                    href={`${repo}/blob/main/DISCLAIMER.md`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={DOC_LINK}
                  >
                    免责说明
                  </a>
                  。
                </li>
              </ul>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
