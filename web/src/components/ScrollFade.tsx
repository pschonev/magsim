import { type ReactNode, useCallback, useEffect, useRef, useState } from "react";

const EDGE_TOLERANCE_PX = 2;

interface ScrollFadeProps {
  children: ReactNode;
  /** Classes of the outer box (border, radius, margins). */
  className?: string;
  /** Classes of the scrolling element (e.g. a max height on larger screens). */
  scrollerClassName?: string;
  /** Gradient start colour matching the surface behind the scroller. */
  fadeFrom?: string;
  hideScrollbar?: boolean;
}

/** Horizontal scroller that fades its edges while more content is hidden on that side. */
export function ScrollFade({
  children,
  className = "",
  scrollerClassName = "",
  fadeFrom = "from-slate-950",
  hideScrollbar = false,
}: ScrollFadeProps) {
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const [edges, setEdges] = useState({ start: false, end: false });

  const measure = useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const start = el.scrollLeft > EDGE_TOLERANCE_PX;
    const end = el.scrollLeft + el.clientWidth < el.scrollWidth - EDGE_TOLERANCE_PX;
    setEdges((prev) => (prev.start === start && prev.end === end ? prev : { start, end }));
  }, []);

  useEffect(measure);

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    Array.from(el.children).forEach((child) => observer.observe(child));
    return () => observer.disconnect();
  }, [measure]);

  return (
    <div className={`relative ${className}`}>
      <div
        ref={scrollerRef}
        onScroll={measure}
        className={`overflow-x-auto ${hideScrollbar ? "no-scrollbar" : ""} ${scrollerClassName}`}
      >
        {children}
      </div>
      {edges.start && (
        <span
          aria-hidden="true"
          className={`pointer-events-none absolute inset-y-0 left-0 z-20 w-8 rounded-l-[inherit] bg-linear-to-r ${fadeFrom} to-transparent`}
        />
      )}
      {edges.end && (
        <span
          aria-hidden="true"
          className={`pointer-events-none absolute inset-y-0 right-0 z-20 w-8 rounded-r-[inherit] bg-linear-to-l ${fadeFrom} to-transparent`}
        />
      )}
    </div>
  );
}
