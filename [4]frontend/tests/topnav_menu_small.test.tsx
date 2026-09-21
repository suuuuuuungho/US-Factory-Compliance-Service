// SUU-213: 상단바 가운데 메뉴 글씨는 한 단계 작게(text-sm). 제목은 그대로.
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import TopNav from "../src/app/TopNav";

it("메뉴 nav에 text-sm 이 있고 제목 링크에는 없다", () => {
  render(<TopNav />);
  expect(screen.getByRole("navigation").classList.contains("text-sm")).toBe(true);
  const title = screen.getByRole("link", { name: "US Factory Compliance AI Service" });
  expect(title.classList.contains("text-sm")).toBe(false);
});
