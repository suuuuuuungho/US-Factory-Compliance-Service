// SUU-186: About / Applicability 빈 페이지. h1 제목만 있다. (SUU-218: Amendment/Community 는 nav_menu.test.tsx 로)
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import About from "../src/app/about/page";
import Applicability from "../src/app/applicability/page";

const pages = [
  ["About", About],
  ["Applicability", Applicability],
] as const;

for (const [title, Page] of pages) {
  it(`/${title.toLowerCase()} 페이지 h1이 ${title} 다`, () => {
    render(<Page />);
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(title);
  });
}
