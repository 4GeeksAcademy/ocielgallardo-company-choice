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

type LazySectionComponent = ComponentType<Record<string, unknown>>;

export function createLazyViewportSection(
  loader: () => Promise<{ default: LazySectionComponent }>,
  options: CreateLazyViewportSectionOptions = {},
) {
  const fallback =
    options.fallback ?? (
      <SectionPlaceholder
        minHeight={options.minHeight ?? 280}
        label={options.label ?? "Loading section…"}
      />
    );

  const DynamicComponent = dynamic(loader, { loading: () => fallback });

  function LazyViewportSection(props: Record<string, unknown> = {}) {
    return (
      <LazyWhenVisible
        fallback={fallback}
        rootMargin={options.rootMargin}
        minHeight={options.minHeight}
      >
        <DynamicComponent {...props} />
      </LazyWhenVisible>
    );
  }

  return LazyViewportSection;
}
