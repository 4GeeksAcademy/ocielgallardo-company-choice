import Link from "next/link";
import { PatientApplicationForm } from "@/components/forms/PatientApplicationForm";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { SiteHeader } from "@/components/layout/SiteHeader";

export default function ApplicationPage() {
  return (
    <div>
      <SiteHeader />
      <main className="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900 sm:p-6">
          <Link href="/" className="text-sm font-medium text-(--brand-fg) hover:underline">
            ← Back to website
          </Link>
          <h1 className="mt-3 text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">
            Patient Application Form
          </h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Request an appointment or intake callback from HealthCore patient access teams.
          </p>

          <div className="mt-6">
            <PatientApplicationForm />
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
