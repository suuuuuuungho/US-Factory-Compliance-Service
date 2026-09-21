// SUU-162: vitest 배선 확인. 루트 페이지(src/app/page.tsx)가 렌더되고 <main>이 있다.
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import Home from "../src/app/page";

it("루트 페이지가 렌더된다", () => {
  render(<Home />);
  expect(screen.getByRole("main")).toBeTruthy();
});
