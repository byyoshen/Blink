import { useEffect, useState } from "react";
import { useActiveSection, type Theme } from "../hooks";
import MascotSwap from "./MascotSwap";
import ThemeGlyph from "./ThemeGlyph";

interface NavProps {
  repo: string;
  theme: Theme;
  toggleTheme: () => void;
  /** Whether the page sections exist yet; they mount only after the data loads. */
  sectionsMounted: boolean;
}

/* Menu order, top to bottom: 使用 first, because that is what the hero's
   primary CTA points at -- the menu should open on the same door the page
   offers. The rest follow in build order. */
const NAV_LINKS = [
  { href: "#usage", label: "使用" },
  { href: "#rulesets", label: "规则集" },
  { href: "#profiles", label: "配置文件" },
  { href: "#about", label: "构建与来源" },
] as const;

/* Document order, which the menu order above is no longer. useActiveSection
   breaks a tie between two visible sections by taking the earlier id in this
   list, and "earlier" has to mean earlier on the page: menu order would
   highlight 使用 while the reader is still inside 规则集. */
const SECTION_IDS = ["rulesets", "usage", "profiles", "about"];

/* Shape encodes role, which is what keeps the bar coherent rather than merely
   decorated: a borderless pill is in-page navigation, a bordered pill is an
   action that leaves the site, a circle is an icon-only control. */
const NAV_ITEM =
  "rounded-full px-3 py-1.5 text-sm font-medium tracking-[0.01em] transition-[color,background-color,transform] duration-150 ease-out active:scale-[0.97]";

/** GitHub's own mark, used to link to GitHub — see THIRD_PARTY_NOTICES. */
function GitHubMark() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" className="h-[15px] w-[15px] fill-current">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
    </svg>
  );
}

export default function Nav({ repo, theme, toggleTheme, sectionsMounted }: NavProps) {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const activeSection = useActiveSection(SECTION_IDS, sectionsMounted);
  const dark = theme === "dark";
  const themeLabel = dark ? "切换到浅色主题" : "切换到深色主题";

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className="fixed inset-x-0 top-0 z-50 px-6 pt-3">
      <div
        className={`mx-auto flex h-14 max-w-5xl items-center gap-4 rounded-full px-5 transition-[border-color,background-color,box-shadow] duration-300 ease-out ${
          scrolled || menuOpen ? "nav-scrolled" : "border border-transparent bg-transparent"
        }`}
      >
        <a
          href="#top"
          className="flex items-center gap-2 text-[17px] font-bold tracking-tight text-ink"
        >
          <span className="relative h-6 w-6 shrink-0 overflow-hidden rounded-full border border-line bg-card">
            <MascotSwap dark={dark} />
          </span>
          Blink
        </a>
        <nav className="ml-auto hidden items-center gap-0.5 sm:flex" aria-label="主导航">
          {NAV_LINKS.map((link) => {
            const current = activeSection === link.href.slice(1);
            return (
              <a
                key={link.href}
                href={link.href}
                aria-current={current ? "true" : undefined}
                className={`${NAV_ITEM} ${
                  current ? "bg-accent-soft text-accent" : "text-mute hover:bg-paper hover:text-ink"
                }`}
              >
                {link.label}
              </a>
            );
          })}
        </nav>
        <a
          href={repo}
          target="_blank"
          rel="noopener noreferrer"
          className={`${NAV_ITEM} hidden items-center gap-1.5 border border-line bg-card text-ink hover:border-line-strong hover:bg-paper sm:inline-flex`}
        >
          <GitHubMark />
          GitHub
        </a>
        <button
          type="button"
          onClick={toggleTheme}
          aria-label={themeLabel}
          title={themeLabel}
          className="relative ml-auto flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-line bg-card text-ink transition-all duration-200 ease-out hover:-translate-y-0.5 hover:border-line-strong hover:bg-paper hover:shadow-md active:scale-90 sm:ml-0"
        >
          <span className="relative h-6 w-6">
            <ThemeGlyph dark={dark} />
          </span>
        </button>
        <button
          type="button"
          onClick={() => setMenuOpen((open) => !open)}
          aria-label={menuOpen ? "关闭菜单" : "打开菜单"}
          aria-expanded={menuOpen}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-line bg-card text-ink transition-all duration-200 ease-out hover:bg-paper active:scale-90 sm:hidden"
        >
          {/* Three bars folding into an X, rather than two glyphs trading
              places. The middle bar collapses faster than the outer two travel
              (200ms against 320ms), so it is gone before they arrive. The bars
              are heavy and fully rounded on purpose: hairlines read as drawn
              rules rather than as a button. */}
          <span className="relative block h-[16px] w-[17px]">
            <span
              className={`absolute left-0 h-[3px] w-full rounded-full bg-current transition-all duration-[320ms] ease-[cubic-bezier(0.4,0,0.2,1)] motion-reduce:transition-none ${
                menuOpen ? "top-[6.5px] rotate-45" : "top-0 rotate-0"
              }`}
            />
            <span
              className={`absolute left-0 top-[6.5px] h-[3px] w-full rounded-full bg-current transition-all duration-200 ease-out motion-reduce:transition-none ${
                menuOpen ? "scale-x-0 opacity-0" : "scale-x-100 opacity-100"
              }`}
            />
            <span
              className={`absolute left-0 h-[3px] w-full rounded-full bg-current transition-all duration-[320ms] ease-[cubic-bezier(0.4,0,0.2,1)] motion-reduce:transition-none ${
                menuOpen ? "top-[6.5px] -rotate-45" : "top-[13px] rotate-0"
              }`}
            />
          </span>
        </button>
      </div>

      {menuOpen && (
        <nav
          aria-label="移动端导航"
          className="hero-enter absolute left-6 right-6 top-[68px] overflow-hidden rounded-3xl border border-line bg-card/95 shadow-lg backdrop-blur-md sm:hidden"
          style={{ animationDuration: "0.25s" }}
        >
          {NAV_LINKS.map((link) => {
            const current = activeSection === link.href.slice(1);
            return (
              <a
                key={link.href}
                href={link.href}
                aria-current={current ? "true" : undefined}
                onClick={() => setMenuOpen(false)}
                className={`block border-b border-line px-6 py-3.5 text-sm font-medium tracking-[0.01em] transition-colors duration-150 ease-out ${
                  current ? "bg-accent-soft text-accent" : "text-ink hover:bg-paper"
                }`}
              >
                {link.label}
              </a>
            );
          })}
          <button
            type="button"
            onClick={() => {
              toggleTheme();
              setMenuOpen(false);
            }}
            aria-label={`主题切换 · ${themeLabel}`}
            className="flex w-full items-center border-b border-line px-6 py-3.5 text-left text-sm text-mute transition-colors duration-150 ease-out hover:bg-paper"
          >
            主题切换
          </button>
          <a
            href={repo}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setMenuOpen(false)}
            className="flex items-center gap-2.5 px-6 py-3.5 text-sm text-mute transition-colors duration-150 ease-out hover:bg-paper"
          >
            <GitHubMark />
            GitHub
          </a>
        </nav>
      )}
    </header>
  );
}
