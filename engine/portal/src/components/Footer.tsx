import type { Theme } from "../hooks";

interface FooterProps {
  repo: string;
  theme: Theme;
}

export default function Footer({ repo, theme }: FooterProps) {
  const dark = theme === "dark";
  const links = [
    { label: "GitHub", href: repo },
    { label: "README", href: `${repo}/blob/main/README.md` },
    { label: "审计档案", href: `${repo}/blob/main/SOURCE_AUDITS.md` },
    { label: "第三方声明", href: `${repo}/blob/main/THIRD_PARTY_NOTICES.md` },
  ];
  return (
    <footer className="border-t border-line px-6 py-9">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-3 text-center">
        <p className="flex items-center justify-center gap-2 text-sm font-semibold">
          <span className="relative h-6 w-6 shrink-0 overflow-hidden rounded-full border border-line bg-card">
            <img
              src="blink-logo.png"
              alt=""
              width={24}
              height={24}
              className={`absolute h-full w-full object-cover transition-all duration-300 ease-out ${
                dark ? "rotate-0 scale-100 opacity-100" : "-rotate-180 scale-0 opacity-0"
              }`}
            />
            <img
              src="blink-logo-2.png"
              alt=""
              width={24}
              height={24}
              className={`absolute h-full w-full object-cover transition-all duration-300 ease-out ${
                dark ? "rotate-180 scale-0 opacity-0" : "rotate-0 scale-100 opacity-100"
              }`}
            />
          </span>
          Blink · 多客户端规则与配置
        </p>
        <nav className="flex flex-wrap justify-center gap-4 text-[13.5px]" aria-label="页脚链接">
          {links.map((link) => (
            <a
              key={link.label}
              href={link.href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-mute transition hover:text-ink"
            >
              {link.label}
            </a>
          ))}
        </nav>
        <p className="text-xs text-mute">
          本页数据随每日构建自动刷新 · 使用前请结合自己的客户端日志自行验证
        </p>
      </div>
    </footer>
  );
}
