"use client";

import { createLazyViewportSection } from "@/components/ui/createLazyViewportSection";

export const ServicesSectionLazy = createLazyViewportSection(
  () =>
    import("@/components/sections/ServicesSection").then((mod) => ({
      default: mod.ServicesSection,
    })),
  {
    minHeight: 360,
    label: "Loading services…",
  },
);

export const ImpactSectionLazy = createLazyViewportSection(
  () =>
    import("@/components/sections/ImpactSection").then((mod) => ({
      default: mod.ImpactSection,
    })),
  {
    minHeight: 280,
    label: "Loading impact…",
  },
);

export const FinalCtaSectionLazy = createLazyViewportSection(
  () =>
    import("@/components/sections/FinalCtaSection").then((mod) => ({
      default: mod.FinalCtaSection,
    })),
  {
    minHeight: 220,
    label: "Loading call to action…",
  },
);

export const SiteFooterLazy = createLazyViewportSection(
  () =>
    import("@/components/layout/SiteFooter").then((mod) => ({
      default: mod.SiteFooter,
    })),
  {
    minHeight: 140,
    label: "Loading footer…",
  },
);
