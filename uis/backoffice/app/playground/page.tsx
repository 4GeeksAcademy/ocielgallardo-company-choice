import dynamic from "next/dynamic";
import { LazyWhenVisible } from "@/components/ui/LazyWhenVisible";
import { PanelPlaceholder } from "@/components/ui/PanelPlaceholder";

const Hito2Playground = dynamic(
  () =>
    import("@/components/dashboard/Hito2Playground").then((mod) => ({
      default: mod.Hito2Playground,
    })),
  {
    loading: () => (
      <PanelPlaceholder minHeight={400} label="Loading Hito 2 playground…" />
    ),
  },
);

/** Early visual demo of the Hito 2 domain utilities. Intentionally not linked from the sidebar. */
export default function PlaygroundPage() {
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">
          Hito 2 playground (demo)
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          Interactive demo of the Hito 2 domain utilities. Not part of the daily workflow.
        </p>
      </section>

      <LazyWhenVisible
        fallback={<PanelPlaceholder minHeight={400} label="Loading Hito 2 playground…" />}
        minHeight={400}
      >
        <Hito2Playground />
      </LazyWhenVisible>
    </div>
  );
}
