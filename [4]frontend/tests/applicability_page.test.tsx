// SUU-190: 질문 화면(textarea + Ask + 3열)이 / 에서 /applicability 로 옮겨간다. h1은 Applicability.
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import Applicability from "../src/app/applicability/page";
import Home from "../src/app/page";

it("/applicability 에 질문 textarea + Ask 버튼이 있고 h1이 Applicability 다", () => {
  render(<Applicability />);
  expect(screen.getByRole("textbox")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Ask" })).toBeTruthy();
  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Applicability");
});

it("/ 에는 질문 textarea가 없다", () => {
  render(<Home />);
  expect(screen.queryByRole("textbox")).toBeNull();
});
