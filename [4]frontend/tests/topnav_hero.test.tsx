// SUU-171: 상단바·탭 제목·첫 화면 h1. SUU-185: 상단바·탭 제목을 "Comp.Doc" → "US Factory Compliance AI Service".
import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import Home from "../src/app/page";
import TopNav from "../src/app/TopNav";

// next/font/google은 Next 빌드 밖(vitest)에서 못 돈다 → 가짜로 바꿔서 layout의 metadata만 읽는다
vi.mock("next/font/google", () => ({ Inter: () => ({ variable: "--font-inter" }) }));

it("상단바에 US Factory Compliance AI Service 글자가 보인다", () => {
  render(<TopNav />);
  expect(screen.getByRole("banner")).toBeTruthy();
  expect(screen.getByText("US Factory Compliance AI Service")).toBeTruthy();
  expect(screen.queryByText("Comp.Doc")).toBeNull();
});

// SUU-173: 대소문자 섞은 문구, 한 줄(nowrap). SUU-176: 설명문은 accent-blue. SUU-181: h1 metal 제거
it("첫 화면 h1이 US Factory Compliance AI Service 다", () => {
  render(<Home />);
  const h1 = screen.getByRole("heading", { level: 1 });
  expect(h1.textContent).toBe("US Factory Compliance AI Service");
  expect(h1.classList.contains("whitespace-nowrap")).toBe(true);
});

it("h1은 흰 글자(text-ink)이고 metal·파란 강조는 없다", () => {
  render(<Home />);
  const h1 = screen.getByRole("heading", { level: 1 });
  expect(h1.classList.contains("text-ink")).toBe(true);
  expect(h1.classList.contains("text-metal")).toBe(false);
  expect(h1.querySelector(".text-accent-blue")).toBeNull();
});

it("설명문은 accent-blue 다", () => {
  render(<Home />);
  const p = screen.getByText(/40 CFR Part 63 applicability criteria/);
  expect(p.classList.contains("text-accent-blue")).toBe(true);
});

it("탭 제목(metadata.title)이 US Factory Compliance AI Service 다", async () => {
  const { metadata } = await import("../src/app/layout");
  expect(metadata.title).toBe("US Factory Compliance AI Service");
});
