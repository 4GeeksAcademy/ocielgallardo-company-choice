import { SiteFooter } from "@/components/layout/SiteFooter";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { FinalCtaSection } from "@/components/sections/FinalCtaSection";
import { HeroSection } from "@/components/sections/HeroSection";
import { ImpactSection } from "@/components/sections/ImpactSection";
import { ServicesSection } from "@/components/sections/ServicesSection";
import { LazyWhenVisible } from "@/components/ui/LazyWhenVisible";
import { SectionPlaceholder } from "@/components/ui/SectionPlaceholder";

export default function WebsiteHomePage() {
  return (
    <div>
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        <HeroSection />

        <LazyWhenVisible
          fallback={<SectionPlaceholder minHeight={360} label="Loading services…" />}
          minHeight={360}
        >
          <ServicesSection />
        </LazyWhenVisible>

        <LazyWhenVisible
          fallback={<SectionPlaceholder minHeight={280} label="Loading impact…" />}
          minHeight={280}
        >
          <ImpactSection />
        </LazyWhenVisible>

        <LazyWhenVisible
          fallback={<SectionPlaceholder minHeight={220} label="Loading call to action…" />}
          minHeight={220}
        >
          <FinalCtaSection />
        </LazyWhenVisible>
      </main>

      <LazyWhenVisible
        fallback={<SectionPlaceholder minHeight={140} label="Loading footer…" />}
        minHeight={140}
      >
        <SiteFooter />
      </LazyWhenVisible>
    </div>
  );
}
