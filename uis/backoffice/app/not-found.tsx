import Link from "next/link";

export default function NotFound() {
  return (
    <section className="mx-auto max-w-lg space-y-4 rounded-xl border border-slate-200 bg-white p-6 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <p className="text-sm font-semibold text-primary">404</p>
      <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Page not found</h1>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        The page you are looking for does not exist or has moved.
      </p>
      <Link
        href="/"
        className="inline-block rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
      >
        Go to dashboard
      </Link>
    </section>
  );
}
