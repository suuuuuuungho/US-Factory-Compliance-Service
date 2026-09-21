// SUU-171: 상단바에 "Comp.Doc", 첫 화면 h1이 "US FACTORY COMPLIANCE AI SERVICE", 탭 제목이 "Comp.Doc".
import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import Home from "../src/app/page";
import TopNav from "../src/app/TopNav";

// next/font/google은 Next 빌드 밖(vitest)에서 못 돈다 → 가짜로 바꿔서 layout의 metadata만 읽는다
vi.mock("next/font/google", () => ({ Inter: () => ({ variable: "--font-inter" }) }));

it("상단바에 Comp.Doc 글자가 보인다", () => {
  render(<TopNav />);
  expect(screen.getByRole("banner")).toBeTruthy();
  expect(screen.getByText("Comp.Doc")).toBeTruthy();
});

// SUU-173: 대소문자 섞은 문구, 한 줄(nowrap), "AI Service"만 accent-blue
it("첫 화면 h1이 US Factory Compliance AI Service 다", () => {
  render(<Home />);
  const h1 = screen.getByRole("heading", { level: 1 });
  expect(h1.textContent).toBe("US Factory Compliance AI Service");
  expect(h1.classList.contains("whitespace-nowrap")).toBe(true);
});

it("h1의 AI Service 부분만 accent-blue 다", () => {
  render(<Home />);
  const em = screen.getByText("AI Service");
  expect(em.classList.contains("text-accent-blue")).toBe(true);
  expect(em.closest("h1")).toBeTruthy();
});

it("탭 제목(metadata.title)이 Comp.Doc 이다", async () => {
  const { metadata } = await import("../src/app/layout");
  expect(metadata.title).toBe("Comp.Doc");
});
