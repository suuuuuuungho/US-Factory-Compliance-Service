// SUU-186: Applicability 빈 페이지. h1 제목만 있다. (SUU-218: Amendment/Community 는 nav_menu.test.tsx 로, SUU-217: About 는 about_page.test.tsx 로)
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import Applicability from "../src/app/applicability/page";

it("/applicability 페이지 h1이 Applicability 다", () => {
  render(<Applicability />);
  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Applicability");
});
