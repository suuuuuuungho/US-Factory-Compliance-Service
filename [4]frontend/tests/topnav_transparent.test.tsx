// SUU-212: 상단바 검은 배경·밑줄 없음, 메뉴 4개는 가운데, 글자는 흰색. 랜딩 히어로는 상단바 밑까지 올라온다.
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import Home from "../src/app/page";
import TopNav from "../src/app/TopNav";

it("header에 bg-canvas·border-b 없고, 메뉴 nav가 가운데 칸, 제목·링크가 text-white 다", () => {
  render(<TopNav />);
  const header = screen.getByRole("banner");
  expect(header.classList.contains("bg-canvas")).toBe(false);
  expect(header.classList.contains("border-b")).toBe(false);
  expect(header.classList.contains("grid-cols-[1fr_auto_1fr]")).toBe(true);
  expect(screen.getByRole("navigation").classList.contains("col-start-2")).toBe(true);
  for (const name of ["US Factory Compliance AI Service", "About", "Applicability", "Federal Register", "EPA ECHO", "EPA Decision Letter"]) {
    expect(screen.getByRole("link", { name }).classList.contains("text-white")).toBe(true);
  }
});

it("랜딩 hero section이 min-h-[100dvh] + -mt-[60px] 다", () => {
  render(<Home />);
  const cls = screen.getByRole("region", { name: "Hero" }).classList;
  expect(cls.contains("min-h-[100dvh]")).toBe(true);
  expect(cls.contains("-mt-[60px]")).toBe(true);
});
