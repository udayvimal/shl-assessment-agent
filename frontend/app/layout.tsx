import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SHL Assessment Advisor",
  description: "Conversational agent to help you find the right SHL assessments",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full bg-slate-50 antialiased">{children}</body>
    </html>
  );
}
