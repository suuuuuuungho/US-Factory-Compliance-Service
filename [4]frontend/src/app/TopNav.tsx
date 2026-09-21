// SUU-171: 상단바. DESIGN.md top-nav — 높이 60px, canvas 배경, 하단 hairline.
// SUU-187: 오른쪽에 메뉴 4개 (About / Applicability / Amendment / Community).
import Link from "next/link";

const MENU = [
  ["About", "/about"],
  ["Applicability", "/applicability"],
  ["Amendment", "/amendment"],
  ["Community", "/community"],
] as const;

export default function TopNav() {
  return (
    <header className="flex h-[60px] items-center border-b border-hairline bg-canvas px-6">
      <span className="font-medium text-ink">US Factory Compliance AI Service</span>
      <nav className="ml-auto flex gap-6">
        {MENU.map(([name, href]) => (
          <Link key={href} href={href} className="text-ink hover:opacity-70">
            {name}
          </Link>
        ))}
      </nav>
    </header>
  );
}
