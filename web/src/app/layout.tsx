import type { Metadata } from "next";
import Script from "next/script";
import { Space_Grotesk, Source_Sans_3 } from "next/font/google";
import { WebsiteJsonLd } from "@/components/JsonLd";
import "./globals.css";

const headingFont = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-heading",
  display: "swap",
});

const bodyFont = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.SITE_URL || "https://projectcivitas.com"),
  title: "Civitas - Protecting American Democracy",
  description:
    "Fighting Project 2025 implementation to protect American democracy. Monitor threats, understand impacts, and take action.",
  keywords: [
    "Project 2025",
    "democracy",
    "legislation tracker",
    "executive orders",
    "civic engagement",
    "resistance",
  ],
  authors: [{ name: "Project Civitas" }],
  openGraph: {
    title: "Civitas - Protecting American Democracy",
    description:
      "Fighting Project 2025 implementation to protect American democracy.",
    url: "https://projectcivitas.com",
    siteName: "Civitas",
    type: "website",
    images: [
      {
        url: "/og?title=Civitas&subtitle=Protecting+American+Democracy&type=page",
        width: 1200,
        height: 630,
        alt: "Civitas - Protecting American Democracy",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Civitas - Protecting American Democracy",
    description:
      "Fighting Project 2025 implementation to protect American democracy.",
    images: [
      "/og?title=Civitas&subtitle=Protecting+American+Democracy&type=page",
    ],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${bodyFont.variable} ${headingFont.variable} min-h-screen font-sans`}
      >
        <Script
          id="theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: `
(() => {
  const key = "civitas-theme";
  const stored = localStorage.getItem(key);
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const isDark = stored ? stored === "dark" : prefersDark;
  document.documentElement.classList.toggle("dark", isDark);
})();
            `,
          }}
        />
        <WebsiteJsonLd />
        {children}
      </body>
    </html>
  );
}
