"use client";

import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";

interface LazyWhenVisibleProps {
  children: ReactNode;
  fallback?: ReactNode;
  rootMargin?: string;
  threshold?: number;
  minHeight?: number | string;
  className?: string;
}

export function LazyWhenVisible({
  children,
  fallback = null,
  rootMargin = "200px 0px",
  threshold = 0,
  minHeight,
  className,
}: LazyWhenVisibleProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || isVisible) return;

    if (typeof IntersectionObserver === "undefined") {
      setIsVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin, threshold },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [isVisible, rootMargin, threshold]);

  const style: CSSProperties | undefined =
    minHeight !== undefined ? { minHeight } : undefined;

  return (
    <div
      ref={containerRef}
      className={className}
      style={style}
      role="status"
      aria-live="polite"
      aria-busy={!isVisible}
    >
      {isVisible ? children : fallback}
    </div>
  );
}
