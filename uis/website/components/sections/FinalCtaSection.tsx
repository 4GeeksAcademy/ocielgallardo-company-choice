import Link from "next/link";

export function FinalCtaSection() {
  return (
    <section className="mt-12 rounded-2xl bg-gradient-to-r from-[var(--primary-900)] to-[var(--primary-700)] px-5 py-8 text-white shadow-sm sm:px-8 sm:py-10">
      <h2 className="text-2xl font-bold sm:text-3xl">Need care access support?</h2>
      <p className="mt-2 max-w-2xl text-sm text-blue-100 sm:text-base">
        Start your request and our patient access team will route your intake to the right clinic pathway.
      </p>
      <Link
        href="/application"
        className="mt-5 inline-block rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-[var(--primary-900)] transition hover:bg-blue-50"
      >
        Open patient application form
      </Link>
    </section>
  );
}
