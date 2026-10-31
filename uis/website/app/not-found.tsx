import Link from "next/link";

export default function NotFound() {
  return (
    <main
      id="main-content"
      tabIndex={-1}
      className="mx-auto flex min-h-[60vh] w-full max-w-xl flex-col items-center justify-center gap-4 px-4 py-12 text-center focus:outline-none"
    >
      <p className="text-sm font-semibold text-primary-600 dark:text-blue-300">404</p>
      <h1 className="font-serif text-2xl font-bold text-slate-900 dark:text-slate-50">Page not found</h1>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        The page you are looking for does not exist or has moved.
      </p>
      <Link
        href="/"
        className="rounded-lg bg-primary-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-primary-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2"
      >
        Back to home
      </Link>
    </main>
  );
}
