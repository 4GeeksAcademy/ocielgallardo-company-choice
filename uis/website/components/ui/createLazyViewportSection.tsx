"use client";

import dynamic from "next/dynamic";
import type { ComponentType, ReactNode } from "react";
import { LazyWhenVisible } from "@/components/ui/LazyWhenVisible";
import { SectionPlaceholder } from "@/components/ui/SectionPlaceholder";

interface CreateLazyViewportSectionOptions {
  fallback?: ReactNode;
  rootMargin?: string;
  minHeight?: number | string;
  label?: string;
}

export function createLazyViewportSection<P extends Record<string, unknown> = Record<string, never>>(
  loader: () => Promise<{ default: ComponentType<P> }>,
  options: CreateLazyViewportSectionOptions = {},
) {
  const fallback =
    options.fallback ?? (
      <SectionPlaceholder
        minHeight={options.minHeight ?? 280}
        label={options.label ?? "Loading section…"}
      />
    );

  const DynamicComponent = dynamic(
    () => loader() as Promise<{ default: ComponentType<P> }>,
    { loading: () => fallback },
  );

  function LazyViewportSection(props: P) {
    const Component = DynamicComponent as ComponentType<P>;

    return (
      <LazyWhenVisible
        fallback={fallback}
        rootMargin={options.rootMargin}
        minHeight={options.minHeight}
      >
        <Component {...props} />
      </LazyWhenVisible>
    );
  }

  return LazyViewportSection;
}
