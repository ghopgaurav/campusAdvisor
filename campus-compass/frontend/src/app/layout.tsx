import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Campus Compass — University Advisor for International Students",
  description:
    "Evidence-backed graduate school guidance powered by AI. Find programs, compare costs, and understand your admission chances.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 antialiased">{children}</body>
    </html>
  );
}
