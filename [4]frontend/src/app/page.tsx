// SUU-190: 질문 화면은 /applicability 로 옮겼다.
// SUU-191: 히어로 랜딩. 이미지는 아직 없음, 나중에 배경 이미지로 교체. SUU-192: 보라 gradient 배경은 뺌(다른 페이지처럼 canvas).
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
      </section>
    </main>
  );
}
