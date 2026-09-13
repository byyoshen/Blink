import { useCallback, useEffect, useRef, useState } from "react";
import type { AppEntry, ClientKey } from "../types";
import { CATEGORY_LABELS, clientFileUrl, copyOptionsFor, sourceLine, typeChips } from "../data";
import { copyText } from "../hooks";

/* iOS-like drawer curve: fast to start, long settle. The sheet travels far
   enough that a plain ease-out reads as abrupt at the end. */
const EASE = "cubic-bezier(0.32, 0.72, 0, 1)";
const DURATION = 280;

/* Dismiss thresholds. Distance alone is not enough: a short flick is a clear
   intent to dismiss, so velocity gets its own path. */
const DISMISS_DISTANCE = 120;
const FLICK_DISTANCE = 24;
const FLICK_VELOCITY = 0.5; // px per ms

function reducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

interface AppSheetProps {
  app: AppEntry;
  client: ClientKey;
  rawBase: string;
  onClose: () => void;
}

/** Mobile detail sheet for one app: what the desktop card shows, plus the copy
 *  actions split by semantic segment.
 *
 * Mounted only while open, so the enter transition always runs from the
 * off-screen state. Exit is driven by the same transition and the parent is
 * told to unmount after it finishes.
 */
export default function AppSheet({ app, client, rawBase, onClose }: AppSheetProps) {
  const [shown, setShown] = useState(false);
  const [drag, setDrag] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [copied, setCopied] = useState("");
  const [failed, setFailed] = useState("");

  const sheetRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const pointer = useRef<{ id: number; startY: number; startTime: number } | null>(null);
  const copyTimer = useRef<number | undefined>(undefined);
  const closing = useRef(false);

  const options = copyOptionsFor(rawBase, app, client);
  const chips = typeChips(app, client);
  const dropped =
    client === "egern" || client === "quantumultx" || client === "mihomo"
      ? (app.clients[client].dropped ?? 0)
      : 0;

  const close = useCallback(() => {
    if (closing.current) return;
    closing.current = true;
    if (reducedMotion()) {
      onClose();
      return;
    }
    setShown(false);
    window.setTimeout(onClose, DURATION);
  }, [onClose]);

  // Enter on the frame after mount, so the browser has painted the off-screen
  // state first and the transition has something to animate from.
  useEffect(() => {
    if (reducedMotion()) {
      setShown(true);
      return;
    }
    const frame = requestAnimationFrame(() => setShown(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  // Lock the page behind the sheet; a sheet that scrolls the page under it
  // feels broken, and on touch the two scrolls fight.
  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  // Escape closes; focus moves in on open and back to the trigger on close.
  useEffect(() => {
    const restore = document.activeElement as HTMLElement | null;
    sheetRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      restore?.focus?.();
    };
  }, [close]);

  useEffect(() => () => window.clearTimeout(copyTimer.current), []);

  const copy = (label: string, snippet: string) => {
    void copyText(snippet).then((ok) => {
      setCopied(ok ? label : "");
      setFailed(ok ? "" : label);
      window.clearTimeout(copyTimer.current);
      copyTimer.current = window.setTimeout(() => {
        setCopied("");
        setFailed("");
      }, 1600);
    });
  };

  const onPointerDown = (event: React.PointerEvent) => {
    // One finger owns the drag. Without this, switching fingers mid-gesture
    // makes the sheet jump to the new contact point.
    if (pointer.current) return;
    // Only start a drag from the top of the content, otherwise a downward
    // swipe meant to scroll the sheet would dismiss it instead.
    if ((scrollRef.current?.scrollTop ?? 0) > 0) return;
    pointer.current = { id: event.pointerId, startY: event.clientY, startTime: Date.now() };
    setDragging(true);
    try {
      sheetRef.current?.setPointerCapture(event.pointerId);
    } catch {
      /* Pointer already released; the drag still tracks over the sheet. */
    }
  };

  const onPointerMove = (event: React.PointerEvent) => {
    const start = pointer.current;
    if (!start || event.pointerId !== start.id) return;
    const delta = event.clientY - start.startY;
    // Dragging up past the resting position is damped rather than blocked:
    // real objects slow down before they stop, they do not hit a wall.
    setDrag(delta > 0 ? delta : delta / 6);
  };

  const onPointerUp = (event: React.PointerEvent) => {
    const start = pointer.current;
    if (!start || event.pointerId !== start.id) return;
    const delta = event.clientY - start.startY;
    const velocity = Math.abs(delta) / Math.max(1, Date.now() - start.startTime);
    pointer.current = null;
    setDragging(false);
    setDrag(0);
    if (delta > DISMISS_DISTANCE || (delta > FLICK_DISTANCE && velocity > FLICK_VELOCITY)) {
      close();
    }
  };

  const offset = shown ? Math.max(0, drag) : null;
  const titleId = `sheet-${app.name}`;

  return (
    <div className="fixed inset-0 z-[120] sm:hidden">
      <div
        onClick={close}
        aria-hidden="true"
        className="absolute inset-0 bg-black/45 transition-opacity duration-300 ease-out motion-reduce:transition-none"
        style={{ opacity: shown ? 1 : 0 }}
      />
      <div
        ref={sheetRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        className="absolute inset-x-0 bottom-0 max-h-[86vh] touch-pan-y overflow-hidden rounded-t-3xl border-t border-line bg-card shadow-2xl outline-none"
        style={{
          transform: offset === null ? "translateY(100%)" : `translateY(${offset}px)`,
          transition: dragging ? "none" : `transform ${DURATION}ms ${EASE}`,
        }}
      >
        <div className="flex justify-center pb-1 pt-2.5">
          <span className="h-1 w-9 rounded-full bg-line-strong" />
        </div>

        <div ref={scrollRef} className="max-h-[calc(86vh-2rem)] overflow-y-auto px-5 pb-7">
          <div className="flex items-center gap-3 pb-4 pt-1">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-line bg-paper">
              {app.icon ? (
                <img src={app.icon} alt="" className="h-full w-full object-cover" />
              ) : (
                <span className="text-xl">{app.emoji}</span>
              )}
            </span>
            <div className="min-w-0">
              <h3 id={titleId} className="truncate text-base font-semibold tracking-tight">
                {app.name}
              </h3>
              <p className="truncate text-[12.5px] text-mute">
                {CATEGORY_LABELS[app.category] ?? app.category} ·{" "}
                <b className="font-semibold text-accent">{app.clients[client].rules}</b> 条规则
              </p>
            </div>
            <button
              type="button"
              onClick={close}
              aria-label="关闭"
              className="ml-auto flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-line bg-paper text-mute transition-transform duration-150 ease-out active:scale-90"
            >
              ✕
            </button>
          </div>

          {chips.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pb-3">
              {chips.map((chip) => (
                <span
                  key={chip.label}
                  className="rounded-full border border-line bg-paper px-2 py-0.5 text-[11.5px] text-mute"
                >
                  {chip.label} <b className="font-semibold text-ink">{chip.count}</b>
                </span>
              ))}
            </div>
          )}

          {app.self_use && (
            <p className="mb-2 rounded-xl border border-accent-soft bg-accent-soft px-3 py-2 text-[12px] leading-relaxed text-accent">
              ⚠️ 个人维护的直播源 · 请按自身直播源自行配置
            </p>
          )}
          {dropped > 0 && (
            <p className="mb-2 rounded-xl border border-line bg-paper px-3 py-2 text-[12px] leading-relaxed text-mute">
              ⚠️ {dropped} 条 {client === "mihomo" ? "USER-AGENT" : "PROCESS-NAME"} 无法在{" "}
              {client === "egern" ? "Egern" : client === "mihomo" ? "mihomo" : "Quantumult X"}{" "}
              无损表达，构建器已显式丢弃。
            </p>
          )}

          <div className="flex flex-col gap-2 border-t border-line pt-4">
            {options.length > 1 && (
              <p className="text-[12px] text-mute">
                这个 App 分两段引用，按下面的先后顺序放进配置 —— IP 段必须在后。
              </p>
            )}
            {options.map((option) => {
              const isCopied = copied === option.label;
              const isFailed = failed === option.label;
              return (
                <button
                  key={option.label}
                  type="button"
                  onClick={() => copy(option.label, option.snippet)}
                  className={`flex w-full items-center gap-2 rounded-xl px-4 py-3 text-left transition-[background-color,color,transform] duration-150 ease-out active:scale-[0.98] ${
                    isCopied ? "bg-accent-strong text-white" : "bg-accent text-white"
                  }`}
                >
                  <span className="text-sm font-medium">
                    {isCopied ? "已复制 ✓" : isFailed ? "复制失败，请重试" : `复制${option.label}`}
                  </span>
                  {option.detail && (
                    <span className="ml-auto truncate text-[11px] text-white/70">
                      {option.detail}
                    </span>
                  )}
                </button>
              );
            })}
            <a
              href={clientFileUrl(rawBase, app, client)}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-xl border border-line bg-paper px-4 py-3 text-center text-sm font-medium text-ink transition-transform duration-150 ease-out active:scale-[0.98]"
            >
              查看规则文件 ↗
            </a>
            <p className="pt-1 text-center text-[11.5px] text-mute">{sourceLine(app)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
