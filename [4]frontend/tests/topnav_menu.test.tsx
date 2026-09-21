// SUU-187: 상단바 메뉴 4개. 누르면 각 페이지로 간다.
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import TopNav from "../src/app/TopNav";

it("상단바에 메뉴 링크 4개가 있고 href가 맞다", () => {
  render(<TopNav />);
  const expected = [
    ["About", "/about"],
    ["Applicability", "/applicability"],
    ["Amendment", "/amendment"],
    ["Community", "/community"],
  ];
  for (const [name, href] of expected) {
    expect(screen.getByRole("link", { name }).getAttribute("href")).toBe(href);
  }
  expect(screen.getByText("US Factory Compliance AI Service")).toBeTruthy();
});
