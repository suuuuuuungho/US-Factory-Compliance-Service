// SUU-215: /applicability 제목은 28px 굵게, PromptBar 는 640px, 아래 예시 질문 3개를 누르면 Prompt 칸에 올라간다.
// SUU-217: About h1이 큰 serif 제목이 되어, 기준을 About 대신 클래스 문자열로 바꿈.
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import Applicability from "../src/app/applicability/page";

it("h1 클래스가 28px 굵게 New York(font-serif)다", () => {
  render(<Applicability />);
  expect(screen.getByRole("heading", { level: 1 }).className).toBe("font-serif text-[28px] font-bold text-ink");
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

it("Ask 전에는 main 이 가운데 정렬(items-center text-center)이고 Prompt 안내문은 'Ask what you want to know' 다", () => {
  render(<Applicability />);
  const main = screen.getByRole("main").classList;
  expect(main.contains("items-center")).toBe(true);
  expect(main.contains("text-center")).toBe(true);
  expect(screen.getByRole("textbox", { name: "Prompt" }).getAttribute("placeholder")).toBe("Ask what you want to know");
});
