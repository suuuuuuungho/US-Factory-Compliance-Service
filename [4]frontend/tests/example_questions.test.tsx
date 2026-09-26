// SUU-215: /applicability 제목은 28px 굵게, PromptBar 는 640px. 예시 질문 3개는 뺐고 대신 작성 안내(How to write)가 있다.
// SUU-217: About h1이 큰 serif 제목이 되어, 기준을 About 대신 클래스 문자열로 바꿈.
import { render, screen } from "@testing-library/react";
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

it("예시 질문 목록은 없고, PromptBar 아래에 작성 안내 4줄(Where·Size·Process·Question)이 있다", () => {
  render(<Applicability />);
  expect(screen.queryByRole("list", { name: "Example questions" })).toBeNull();
  const howTo = screen.getByRole("region", { name: "How to write your question" });
  const items = howTo.querySelectorAll("li");
  expect(items.length).toBe(4);
  expect(Array.from(items).map((li) => li.textContent)).toEqual([
    "Where — State, and what the plant makes",
    "Size — Major or area source of HAP",
    "Process — Equipment, materials, and how it runs",
    "Question — Which rule or requirement you want checked",
  ]);
});

it("Ask 전에는 main 이 가운데 정렬(items-center text-center)이고 Prompt 안내문은 'Ask what you want to know' 다", () => {
  render(<Applicability />);
  const main = screen.getByRole("main").classList;
  expect(main.contains("items-center")).toBe(true);
  expect(main.contains("text-center")).toBe(true);
  expect(screen.getByRole("textbox", { name: "Prompt" }).getAttribute("placeholder")).toBe("Ask what you want to know");
});
