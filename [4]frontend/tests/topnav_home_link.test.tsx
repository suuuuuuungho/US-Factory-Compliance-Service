// SUU-202: 상단바 제목을 누르면 히어로 랜딩페이지(/)로 간다.
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import TopNav from "../src/app/TopNav";

it("상단바 제목이 / 로 가는 링크다", () => {
  render(<TopNav />);
  const link = screen.getByRole("link", { name: "US Factory Compliance AI Service" });
  expect(link.getAttribute("href")).toBe("/");
});
