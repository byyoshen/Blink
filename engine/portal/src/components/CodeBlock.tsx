import type { ReactNode } from "react";
import { useCopy } from "../hooks";

interface CodeBlockProps {
  file: string;
  copyText: string;
  copyLabel?: string;
  maxHeight?: boolean;
  children: ReactNode;
}

export default function CodeBlock({
  file,
  copyText,
  copyLabel = "复制",
  maxHeight = false,
  children,
}: CodeBlockProps) {
  const { state, copy } = useCopy(copyText);
  return (
    <div className="overflow-hidden rounded-2xl bg-codebg text-left shadow-lg">
      <div className="flex items-center gap-1.5 border-b border-white/10 px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
        <span className="ml-2 font-mono text-xs text-white/50">{file}</span>
        <button
          type="button"
          onClick={copy}
          className="ml-auto rounded-md border border-white/15 bg-white/5 px-2.5 py-1 text-xs text-white/70 transition-all duration-200 ease-out hover:bg-white/10 hover:text-white active:scale-95"
        >
          {state === "done" ? "已复制 ✓" : state === "failed" ? "复制失败" : copyLabel}
        </button>
      </div>
      <pre
        className={`overflow-x-auto px-4 py-4 font-mono text-[13px] leading-relaxed text-[#c6ccd9] ${
          maxHeight ? "max-h-72 overflow-y-auto" : ""
        }`}
      >
        <code>{children}</code>
      </pre>
    </div>
  );
}
