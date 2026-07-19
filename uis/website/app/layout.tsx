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
  icons: {
    icon: [
      { url: "/icons/logo-01.png", type: "image/png", sizes: "48x48" },
      { url: "/icons/logo-01.png", type: "image/png", sizes: "96x96" },
      { url: "/icons/logo-01.png", type: "image/png", sizes: "192x192" },
    ],
    apple: [{ url: "/icons/logo-01.png", sizes: "180x180", type: "image/png" }],
    shortcut: "/icons/logo-01.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${headingFont.variable} ${bodyFont.variable} h-full`}>
      <body className="min-h-full">{children}</body>
    </html>
  );
}
