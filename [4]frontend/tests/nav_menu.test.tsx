// SUU-218: 메뉴 5개 (About / Applicability / Federal Register / EPA ECHO / EPA Decision Letter). Community 없음.
import { existsSync } from "node:fs";
import { join } from "node:path";
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import TopNav from "../src/app/TopNav";
import FederalRegister from "../src/app/federal-register/page";
import Echo from "../src/app/echo/page";
import DecisionLetter from "../src/app/decision-letter/page";

it("TopNav에 링크 5개가 순서대로 있고 href가 맞다", () => {
  render(<TopNav />);
  const links = screen.getAllByRole("link").filter((a) => a.getAttribute("href") !== "/");
  expect(links.map((a) => [a.textContent, a.getAttribute("href")])).toEqual([
    ["About", "/about"],
    ["Applicability", "/applicability"],
    ["Federal Register", "/federal-register"],
    ["EPA ECHO", "/echo"],
    ["EPA Decision Letter", "/decision-letter"],
  ]);
});

it("/federal-register, /echo, /decision-letter 페이지 h1이 맞다", () => {
  const pages = [
    ["Federal Register", FederalRegister],
    ["EPA ECHO", Echo],
    ["EPA Decision Letter", DecisionLetter],
  ] as const;
  for (const [title, Page] of pages) {
    const { unmount } = render(<Page />);
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(title);
    unmount();
  }
});

it("Community 링크와 /community, /amendment 폴더가 없다", () => {
  render(<TopNav />);
  expect(screen.queryByRole("link", { name: "Community" })).toBeNull();
  expect(existsSync(join(__dirname, "../src/app/community"))).toBe(false);
  expect(existsSync(join(__dirname, "../src/app/amendment"))).toBe(false);
});
