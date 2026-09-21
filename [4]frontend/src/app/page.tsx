// SUU-190: 질문 화면은 /applicability 로 옮겼다.
// SUU-191: 히어로 랜딩. 이미지는 아직 없음, 나중에 배경 이미지로 교체. SUU-192: 보라 gradient 배경은 뺌(다른 페이지처럼 canvas).
// SUU-211: 가운데 제목 h1 + 카피 한 줄, New York 세리프. Start 버튼은 없다.
import Image from "next/image";

import HeroSmoke from "./HeroSmoke";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col">
      <section
        aria-label="Hero"
        className="relative flex min-h-[calc(100dvh-60px)] flex-col items-center justify-center overflow-hidden px-8 text-center"
      >
        <Image
          src="/hero-etching.png"
          alt="Factory etching"
          fill
          priority
          className="object-cover"
        />
        <div className="absolute inset-0 z-10 bg-canvas/60" />
        <HeroSmoke left="14%" top="21%" />
        <HeroSmoke left="29%" top="19%" />
        <div className="relative z-30 flex max-w-3xl flex-col items-center gap-4">
          <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink text-balance md:text-[44px] md:leading-[1.15]">
            US Factory Compliance AI Service
          </h1>
          <p className="font-serif text-base font-normal text-ink/70 text-balance md:text-lg">
            Know which 40 CFR Part 63 rules apply to your plant — and why.
          </p>
        </div>
      </section>
    </main>
  );
}
