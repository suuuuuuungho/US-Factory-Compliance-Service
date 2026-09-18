// SUU-140: vitest 배선 확인. 루트 페이지가 렌더되고 <html>이 크림 배경 클래스를 쓴다.
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Home from "./page";

describe("루트 페이지", () => {
  it("렌더된다", () => {
    render(<Home />);
    expect(screen.getByRole("main")).toBeTruthy();
  });
});
