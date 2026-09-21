// SUU-171: 상단바. DESIGN.md top-nav — 높이 60px, canvas 배경, 하단 hairline. 이름만, 메뉴 없음.
export default function TopNav() {
  return (
    <header className="flex h-[60px] items-center border-b border-hairline bg-canvas px-6">
      <span className="font-medium text-ink">US Factory Compliance AI Service</span>
    </header>
  );
}
