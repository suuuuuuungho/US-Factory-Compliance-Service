// SUU-190: 질문 화면은 /applicability 로 옮겼다.
// SUU-191: 히어로 랜딩. 이미지는 아직 없어서 gradient 배경으로 자리만 잡음. 나중에 이미지로 교체.
import Link from "next/link";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col">
      <section
        aria-label="Hero"
        className="flex min-h-[calc(100dvh-60px)] flex-col items-center justify-center gap-6 bg-gradient-violet px-8 text-center"
      >
        <h1 className="whitespace-nowrap text-2xl font-medium leading-none tracking-[-0.04em] text-ink sm:text-4xl md:text-[2.75rem]">
          US Factory Compliance AI Service
        </h1>
        <p className="text-lg text-accent-blue">
          40 CFR Part 63 applicability criteria, with the sections to check.
        </p>
        <Link
          href="/applicability"
          className="rounded-full bg-primary px-6 py-3 text-sm font-medium text-on-primary hover:opacity-90"
        >
          Start
        </Link>
      </section>
    </main>
  );
}
