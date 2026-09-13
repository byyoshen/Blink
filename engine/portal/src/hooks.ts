import { useCallback, useEffect, useRef, useState } from "react";

function fallbackCopy(text: string): void {
  const area = document.createElement("textarea");
  area.value = text;
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  try {
    document.execCommand("copy");
  } catch {
    /* ignore */
  }
  document.body.removeChild(area);
}

export function useCopy(text: string, copiedMs = 1600): { copied: boolean; copy: () => void } {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const copy = useCallback(() => {
    const done = () => {
      setCopied(true);
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setCopied(false), copiedMs);
    };
    if (navigator.clipboard?.writeText) {
      navigator.clipboard
        .writeText(text)
        .then(done)
        .catch(() => {
          fallbackCopy(text);
          done();
        });
    } else {
      fallbackCopy(text);
      done();
    }
  }, [text, copiedMs]);

  return { copied, copy };
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
