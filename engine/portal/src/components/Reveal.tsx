import { useEffect, useRef, useState, type ReactNode } from "react";

/* Read synchronously, not in the effect. An effect runs after the first paint,
   so deciding there still renders one frame of the hidden state and then
   transitions out of it -- which is motion, and motion is the one thing this
   setting asks us not to produce. Initialising the state from it instead means
   there is no class change at all, so nothing has anything to animate. */
function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

interface RevealProps {
  children: ReactNode;
  className?: string;
  delay?: number;
}

export default function Reveal({ children, className = "", delay = 0 }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(prefersReducedMotion);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (typeof IntersectionObserver === "undefined" || prefersReducedMotion()) {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisible(true);
            observer.disconnect();
          }
        }
      },
      { threshold: 0.12 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`${className} transition-[opacity,transform,filter] duration-500 ease-out motion-reduce:transition-none ${
        visible ? "translate-y-0 opacity-100 blur-0" : "translate-y-3.5 opacity-0 blur-[6px]"
      }`}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </div>
  );
}
