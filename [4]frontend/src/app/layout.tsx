import type { Metadata } from "next";
import { Source_Serif_4 } from "next/font/google";
import "./globals.css";

// 제목·본문 모두 Source Serif 4 Regular(400). 굵기는 제목만 600.
const sourceSerif = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin"],
  weight: ["400", "600"],
});

export const metadata: Metadata = {
  title: "US Factory Compliance",
  description:
    "미국 제조업 공장에 적용될 수 있는 Part 63 규제 조항 후보와 판정 기준을 근거 조문과 함께 정리한다.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      className={`${sourceSerif.variable} h-full bg-paper text-ink antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
