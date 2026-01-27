import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
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
  },
  twitter: {
    card: "summary_large_image",
    title: "Civitas - Protecting American Democracy",
    description:
      "Fighting Project 2025 implementation to protect American democracy.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>{children}</body>
    </html>
  );
}
