import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { AppChrome } from "@/components/layout/AppChrome";
import { WebVitalsReporter } from "@/components/WebVitalsReporter";
import { THEME_INIT_SCRIPT } from "@/lib/theme";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "HealthCore Backoffice",
  description:
    "Internal workspace for HealthCore operations, pipeline management, and analytics demos.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={`${inter.variable} h-full`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="min-h-full bg-slate-50 dark:bg-slate-800 font-sans text-slate-900 dark:text-slate-50 antialiased dark:bg-slate-950 dark:text-slate-100">
        <AppChrome>{children}</AppChrome>
        <WebVitalsReporter />
      </body>
    </html>
  );
}
