export default function Hero() {
  return (
    <section className="mx-auto max-w-6xl px-6 py-24">
      <h1 className="font-serif text-4xl font-semibold leading-tight md:text-5xl">
        우리 공장에 적용될 규제 조항 후보와 판정 기준을, 근거 조문과 함께
      </h1>
      <p className="mt-6 max-w-2xl text-lg text-ink/80">
        미국 제조업 공장의 환경·규제 담당자를 위한 40 CFR Part 63 컴플라이언스 문서 작성 도우미.
        답을 대신 정하지 않고, 어디를 봐야 하고 무엇을 확인해야 하는지를 근거와 함께 보여줍니다.
      </p>
      <a
        href="#"
        className="mt-8 inline-block rounded-sm bg-ink px-6 py-3 text-paper transition hover:opacity-90"
      >
        조항 후보 찾기
      </a>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        alt="판화로 그린 공장 풍경"
        className="parallax mx-auto mt-16 w-full max-w-4xl"
        data-testid="hero-art"
        src="/engraving/hero.png"
      />
    </section>
  );
}
