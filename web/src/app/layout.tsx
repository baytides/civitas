import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Civitas - Tracking Project 2025 Implementation",
  description:
    "Monitor legislative and executive actions implementing Project 2025. Track threats to democracy and find ways to resist.",
  keywords: [
    "Project 2025",
    "democracy",
    "legislation tracker",
    "executive orders",
    "civic engagement",
    "resistance",
  ],
  authors: [{ name: "Civitas Project" }],
  openGraph: {
    title: "Civitas - Tracking Project 2025 Implementation",
    description:
      "Monitor legislative and executive actions implementing Project 2025.",
    url: "https://projectcivitas.com",
    siteName: "Civitas",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Civitas - Tracking Project 2025 Implementation",
    description:
      "Monitor legislative and executive actions implementing Project 2025.",
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
