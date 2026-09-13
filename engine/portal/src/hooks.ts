import { useCallback, useEffect, useRef, useState } from "react";

function fallbackCopy(text: string): boolean {
  const area = document.createElement("textarea");
  area.value = text;
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  document.body.removeChild(area);
  return ok;
}

/** Copy text, reporting whether it actually worked.
 *
 * `navigator.clipboard` is undefined on insecure origins, so the optional call
 * returns undefined rather than a promise -- chaining `.then` onto it throws.
 * Callers need the boolean too: telling someone "copied" when it failed leaves
 * them pasting whatever was in the clipboard before.
 */
export async function copyText(text: string): Promise<boolean> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      return fallbackCopy(text);
    }
  }
  return fallbackCopy(text);
}

export type CopyState = "idle" | "done" | "failed";

/** Copy-to-clipboard with a state the caller can show.
 *
 * "failed" exists because a copy really can fail -- an unfocused document
 * rejects the clipboard API, and insecure origins have no clipboard at all.
 * Reporting success anyway leaves someone pasting whatever they copied last
 * and wondering why their config is wrong.
 */
export function useCopy(
  text: string,
  copiedMs = 1600,
): { copied: boolean; state: CopyState; copy: () => void } {
  const [state, setState] = useState<CopyState>("idle");
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const copy = useCallback(() => {
    void copyText(text).then((ok) => {
      setState(ok ? "done" : "failed");
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setState("idle"), copiedMs);
    });
  }, [text, copiedMs]);

  return { copied: state === "done", state, copy };
}

/* Manual theme: persisted in localStorage, falling back to the system
   preference. No time-of-day auto switching. */
export type Theme = "light" | "dark";

function initialTheme(): Theme {
  try {
    const stored = localStorage.getItem("blink-theme");
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    /* storage unavailable (private mode etc.) */
  }
  // Default to dark; light only when the user explicitly switches.
  return "dark";
}

function applyTheme(next: Theme): void {
  document.documentElement.classList.toggle("dark", next === "dark");
}

export function useTheme(): { theme: Theme; toggle: () => void } {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    applyTheme(theme);
    // Sync the browser-tab favicon: dark = circular white cat, light = circular blue dog.
    const icon = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    if (icon) {
      icon.href = theme === "dark" ? "favicon-cat.png" : "favicon-dog.png";
    }
    try {
      localStorage.setItem("blink-theme", theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  const toggle = useCallback(() => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    const apply = () => {
      applyTheme(next);
      setTheme(next);
    };
    // Smooth whole-page cross-fade where the View Transitions API exists;
    // otherwise fall back to the CSS color transition on <body>.
    const viewTransition = (
      document as Document & { startViewTransition?: (cb: () => void) => unknown }
    ).startViewTransition;
    if (typeof viewTransition === "function") {
      viewTransition.call(document, apply);
    } else {
      apply();
    }
  }, [theme]);

  return { theme, toggle };
}

/** The in-page section currently being read, for the nav's active state.
 *
 * The observer's root margin keeps only a band across the upper middle of the
 * viewport live, so the highlight moves when the reader's eye arrives at a
 * section rather than the moment its top edge slips under the nav bar. When
 * the band spans two sections the earlier one wins, which keeps the highlight
 * from flickering at a boundary. Returns null in the hero, where no nav item
 * should be marked current.
 *
 * ``mounted`` exists because the nav renders before the sections do: the portal
 * fetches its data first, so on the nav's own mount every getElementById would
 * return null and the observer would attach to nothing, permanently.
 */
export function useActiveSection(ids: readonly string[], mounted: boolean): string | null {
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    if (!mounted) return;
    const elements = ids
      .map((id) => document.getElementById(id))
      .filter((element): element is HTMLElement => element !== null);
    if (elements.length === 0) return;

    const visible = new Map<string, boolean>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) visible.set(entry.target.id, entry.isIntersecting);
        setActive(ids.find((id) => visible.get(id)) ?? null);
      },
      { rootMargin: "-30% 0px -50% 0px" },
    );
    for (const element of elements) observer.observe(element);
    return () => observer.disconnect();
  }, [ids, mounted]);

  return active;
}

/** Live media-query match.
 *
 * Reads synchronously on first render -- the portal is a client-only SPA, so
 * there is no server pass to disagree with, and initialising from a effect
 * instead would render one frame of the wrong layout.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);

  useEffect(() => {
    const list = window.matchMedia(query);
    const onChange = () => setMatches(list.matches);
    onChange();
    list.addEventListener("change", onChange);
    return () => list.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}
