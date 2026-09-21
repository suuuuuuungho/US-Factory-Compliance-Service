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

it("첫 화면 h1이 US FACTORY COMPLIANCE AI SERVICE 다", () => {
  render(<Home />);
  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("US FACTORY COMPLIANCE AI SERVICE");
});

it("탭 제목(metadata.title)이 Comp.Doc 이다", async () => {
  const { metadata } = await import("../src/app/layout");
  expect(metadata.title).toBe("Comp.Doc");
});
