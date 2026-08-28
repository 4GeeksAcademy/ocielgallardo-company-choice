"use client";

import dynamic from "next/dynamic";
import type { ComponentType, ReactNode } from "react";
import { LazyWhenVisible } from "@/components/ui/LazyWhenVisible";
import { PanelPlaceholder } from "@/components/ui/PanelPlaceholder";

interface CreateLazyViewportPanelOptions {
  fallback?: ReactNode;
  rootMargin?: string;
  minHeight?: number | string;
  label?: string;
}

type LazyPanelComponent = ComponentType<Record<string, unknown>>;

export function createLazyViewportPanel(
  loader: () => Promise<{ default: LazyPanelComponent }>,
  options: CreateLazyViewportPanelOptions = {},
) {
  const fallback =
    options.fallback ?? (
      <PanelPlaceholder
        minHeight={options.minHeight ?? 320}
        label={options.label ?? "Loading panel…"}
      />
    );

  const DynamicComponent = dynamic(loader, { loading: () => fallback });

  function LazyViewportPanel(props: Record<string, unknown> = {}) {
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

  return LazyViewportPanel;
}
