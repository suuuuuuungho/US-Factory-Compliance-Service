// SUU-171: 상단바. DESIGN.md top-nav — 높이 60px, canvas 배경, 하단 hairline.
// SUU-187: 오른쪽에 메뉴 4개 (About / Applicability / Amendment / Community).
// SUU-202: 제목을 누르면 히어로 랜딩페이지(/)로 간다. SUU-204: 제목은 굵게.
// SUU-212: 배경·밑줄 없음(뒤 화면이 비침). 제목 왼쪽, 메뉴는 가운데 칸, 글자는 흰색. SUU-213: 메뉴는 text-sm.
// SUU-218: 메뉴 5개 (Amendment → Federal Register, EPA ECHO·EPA Decision Letter 추가, Community 삭제).
import Link from "next/link";

const MENU = [
  ["About", "/about"],
  ["Applicability", "/applicability"],
  ["Federal Register", "/federal-register"],
  ["EPA ECHO", "/echo"],
  ["EPA Decision Letter", "/decision-letter"],
] as const;

export default function TopNav() {
  return (
    <header className="relative z-40 grid h-[60px] grid-cols-[1fr_auto_1fr] items-center px-6">
      <Link href="/" className="font-bold text-white">
        US Factory Compliance AI Service
      </Link>
      <nav className="col-start-2 flex gap-6 text-sm">
        {MENU.map(([name, href]) => (
          <Link key={href} href={href} className="text-white hover:opacity-70">
            {name}
          </Link>
        ))}
      </nav>
    </header>
  );
}
