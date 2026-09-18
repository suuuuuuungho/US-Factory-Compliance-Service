const productLinks = ["조항 알림 찾기", "규정 기준", "체크리스트"];
const resourceLinks = ["40 CFR Part 63", "EPA 규정 자료", "개정 이력"];
const companyLinks = ["소개", "문의", "개인정보"];

export default function EngravedFooter() {
  return (
    <footer className="relative overflow-hidden border-t border-line bg-paper" role="contentinfo">
      <div className="mx-auto grid max-w-6xl gap-8 px-6 pb-8 pt-16 md:grid-cols-4">
        <section>
          <p className="font-serif text-xl">US Factory Compliance</p>
          <p className="mt-3 text-sm text-ink/70">규정의 흐름을 공장 현장까지 잇습니다.</p>
          <p className="mt-6 text-xs text-ink/60">© 2026</p>
        </section>
        <FooterLinks title="제품" links={productLinks} />
        <FooterLinks title="자료" links={resourceLinks} />
        <FooterLinks title="회사" links={companyLinks} />
      </div>

      <div aria-hidden="true" className="relative h-[40vw] min-h-[220px] max-h-[420px]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          alt=""
          className="absolute bottom-0 left-1/2 w-[min(100%,1400px)] -translate-x-1/2"
          src="/engraving/factory.png"
        />
        <Smoke src="/engraving/smoke-1.png" left="25%" delay="0s" />
        <Smoke src="/engraving/smoke-2.png" left="50%" delay="1.3s" />
        <Smoke src="/engraving/smoke-3.png" left="73%" delay="2.6s" />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          alt=""
          className="animate-train absolute bottom-[3%] w-[36%] max-w-[520px]"
          data-testid="footer-train"
          src="/engraving/train.png"
        />
      </div>
    </footer>
  );
}

function FooterLinks({ title, links }: { title: string; links: string[] }) {
  return (
    <section>
      <h2 className="font-serif text-base">{title}</h2>
      <ul className="mt-3 space-y-2 text-sm text-ink/70">
        {links.map((link) => (
          <li key={link}>{link}</li>
        ))}
      </ul>
    </section>
  );
}

function Smoke({ src, left, delay }: { src: string; left: string; delay: string }) {
  return (
    /* eslint-disable-next-line @next/next/no-img-element */
    <img
      alt=""
      className="animate-smoke absolute bottom-[10%] w-[7%]"
      data-testid="footer-smoke"
      src={src}
      style={{ left, animationDelay: delay }}
    />
  );
}
