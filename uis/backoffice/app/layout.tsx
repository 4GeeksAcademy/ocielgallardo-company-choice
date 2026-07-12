import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { BackofficeShell } from "@/components/layout/BackofficeShell";
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
    <html lang="es" className={`${inter.variable} h-full`}>
      <body className="min-h-full bg-slate-50 font-sans text-slate-900 antialiased">
        <BackofficeShell>{children}</BackofficeShell>
      </body>
    </html>
  );
}
