import type { Metadata } from "next";
import { Merriweather, Space_Grotesk } from "next/font/google";
import "./globals.css";

const headingFont = Merriweather({
  subsets: ["latin"],
  variable: "--font-merriweather",
});

const bodyFont = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
});

export const metadata: Metadata = {
  title: "HealthCore | Outpatient Care Network",
  description:
    "Public website for HealthCore outpatient care services, patient access, and intake application.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${headingFont.variable} ${bodyFont.variable} h-full`}>
      <body className="min-h-full">{children}</body>
    </html>
  );
}
