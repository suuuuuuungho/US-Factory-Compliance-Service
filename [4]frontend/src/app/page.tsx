// SUU-190: 질문 화면은 /applicability 로 옮겼다. 여기는 임시. SUU-191에서 히어로로 채운다.
export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 p-8">
      <h1 className="whitespace-nowrap text-2xl font-medium leading-none tracking-[-0.04em] text-ink sm:text-4xl md:text-[2.75rem]">
        US Factory Compliance AI Service
      </h1>
      <p className="text-lg text-accent-blue">
        40 CFR Part 63 applicability criteria, with the sections to check.
      </p>
    </main>
  );
}
