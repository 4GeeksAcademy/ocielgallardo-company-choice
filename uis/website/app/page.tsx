import { SiteHeader } from "@/components/layout/SiteHeader";
import {
  FinalCtaSectionLazy,
  ImpactSectionLazy,
  ServicesSectionLazy,
  SiteFooterLazy,
} from "@/components/lazy/lazyViewportSections";
import { HeroSection } from "@/components/sections/HeroSection";

export default function WebsiteHomePage() {
  return (
    <div>
      <SiteHeader />
      <main id="main-content" tabIndex={-1} className="mx-auto focus:outline-none w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        <HeroSection />
        <ServicesSectionLazy />
        <ImpactSectionLazy />
        <FinalCtaSectionLazy />
      </main>
      <SiteFooterLazy />
    </div>
  );
}
