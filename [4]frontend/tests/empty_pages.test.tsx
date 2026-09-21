// SUU-186: About / Applicability / Amendment / Community 빈 페이지 4개. h1 제목만 있다.
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import About from "../src/app/about/page";
import Applicability from "../src/app/applicability/page";
import Amendment from "../src/app/amendment/page";
import Community from "../src/app/community/page";

const pages = [
  ["About", About],
  ["Applicability", Applicability],
  ["Amendment", Amendment],
  ["Community", Community],
] as const;

for (const [title, Page] of pages) {
  it(`/${title.toLowerCase()} 페이지 h1이 ${title} 다`, () => {
    render(<Page />);
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(title);
  });
}
