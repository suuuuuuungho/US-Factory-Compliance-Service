import type { Metadata } from "next";
import { Inter, Lora } from "next/font/google";
import "./globals.css";

const lora = Lora({ variable: "--font-lora", subsets: ["latin"] });
const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "US Factory Compliance",
  description:
    "미국 제조업 공장에 적용될 수 있는 Part 63 규제 조항 후보와 판정 기준을 근거 조문과 함께 정리한다.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      className={`${lora.variable} ${inter.variable} h-full bg-paper text-ink antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
