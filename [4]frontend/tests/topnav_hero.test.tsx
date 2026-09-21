// SUU-171: 상단바·탭 제목·첫 화면 h1. SUU-185: 상단바·탭 제목을 "Comp.Doc" → "US Factory Compliance AI Service".
// SUU-203: 첫 화면 h1·설명문은 없앴다 (hero_flag_etching.test.tsx). 여기는 상단바·탭 제목만.
import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import TopNav from "../src/app/TopNav";

// next/font/local은 Next 빌드 밖(vitest)에서 못 돈다 → 가짜로 바꿔서 layout의 metadata만 읽는다 (SUU-204: Inter → SF Pro)
vi.mock("next/font/local", () => ({ default: () => ({ variable: "--font-sf-pro" }) }));

it("상단바에 US Factory Compliance AI Service 글자가 보인다", () => {
  render(<TopNav />);
  expect(screen.getByRole("banner")).toBeTruthy();
  expect(screen.getByText("US Factory Compliance AI Service")).toBeTruthy();
  expect(screen.queryByText("Comp.Doc")).toBeNull();
});

it("탭 제목(metadata.title)이 US Factory Compliance AI Service 다", async () => {
  const { metadata } = await import("../src/app/layout");
  expect(metadata.title).toBe("US Factory Compliance AI Service");
});
