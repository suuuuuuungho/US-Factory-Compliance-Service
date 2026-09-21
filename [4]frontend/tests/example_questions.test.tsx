// SUU-215: /applicability 제목은 About 과 같은 28px, PromptBar 는 640px, 아래 예시 질문 3개를 누르면 Prompt 칸에 올라간다.
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import About from "../src/app/about/page";
import Applicability from "../src/app/applicability/page";

it("h1 클래스가 About 페이지 h1 과 같다", () => {
  const { unmount } = render(<About />);
  const aboutCls = screen.getByRole("heading", { level: 1 }).className;
  unmount();
  render(<Applicability />);
  expect(screen.getByRole("heading", { level: 1 }).className).toBe(aboutCls);
});

it("PromptBar 너비가 640px 다", () => {
  const { container } = render(<Applicability />);
  expect(container.querySelector<HTMLElement>(".prompt-bar")!.getAttribute("style")).toContain("--pb-w: 640px");
});

it("예시 질문 3개가 있고, 누르면 Prompt 칸에 그 글이 들어가고 Send 가 켜진다", () => {
  render(<Applicability />);
  const examples = screen.getByRole("list", { name: "Example questions" });
  const buttons = examples.querySelectorAll("button");
  expect(buttons.length).toBe(3);
  const send = screen.getByRole("button", { name: "Send" }) as HTMLButtonElement;
  expect(send.disabled).toBe(true);
  fireEvent.click(buttons[1]);
  const box = screen.getByRole("textbox", { name: "Prompt" }) as HTMLTextAreaElement;
  expect(box.value).toBe(buttons[1].textContent);
  expect(box.value).toMatch(/perchloroethylene dry cleaning/);
  expect(send.disabled).toBe(false);
});
