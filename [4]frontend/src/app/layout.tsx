import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import TopNav from "./TopNav";

// SUU-204: 글꼴은 로컬 SF Pro (가변, wght 400~700, 라틴만 60KB).
const sfPro = localFont({
  src: "./fonts/SF-Pro-latin.woff2",
  variable: "--font-sf-pro",
  weight: "400 700",
  display: "swap",
});

export const metadata: Metadata = {
  title: "US Factory Compliance AI Service",
  description: "40 CFR Part 63 applicability criteria",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${sfPro.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <TopNav />
        {children}
      </body>
    </html>
  );
}
