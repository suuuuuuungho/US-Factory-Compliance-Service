// SUU-190: 질문 화면(textarea + Ask + 3열)이 / 에서 /applicability 로 옮겨간다. h1은 Applicability. SUU-214: Ask 버튼은 PromptBar 의 Send.
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import Applicability from "../src/app/applicability/page";
import Home from "../src/app/page";

it("/applicability 에 질문 textarea + Send 버튼이 있고 h1이 eCFR Applicability 다", () => {
  render(<Applicability />);
  expect(screen.getByRole("textbox")).toBeTruthy();
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "x" } }); // SUU-214: 글이 없으면 Send 가 잠겨 있다
  expect(screen.getByRole("button", { name: "Send" })).toBeTruthy();
  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("eCFR Applicability");
});

it("/ 에는 질문 textarea가 없다", () => {
  render(<Home />);
  expect(screen.queryByRole("textbox")).toBeNull();
});
