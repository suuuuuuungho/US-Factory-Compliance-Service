// SUU-216: Send 뒤 답이 올 때까지 "Please wait a moment" 안내문 + 시간에 따라 바뀌는 단계 문구(0s/6s/14s/25s).
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Applicability from "../src/app/applicability/page";
import Waiting, { STEPS } from "../src/app/Waiting";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it("Send 뒤 role=status 안에 'Please wait a moment' 와 첫 단계 문구가 있다", async () => {
  vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {}))); // 영원히 안 끝나는 요청
  render(<Applicability />);
  fireEvent.change(screen.getByRole("textbox", { name: "Prompt" }), { target: { value: "solvent welding" } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  const status = await screen.findByRole("status");
  expect(status.textContent).toContain("Please wait a moment");
  expect(status.textContent).toContain(STEPS[0].text);
});

it("단계 문구가 0초·6초·14초·25초에 차례로 바뀐다", () => {
  vi.useFakeTimers();
  render(<Waiting />);
  expect(STEPS.map((s) => s.at)).toEqual([0, 6, 14, 25]);
  const status = screen.getByRole("status");
  expect(status.textContent).toContain(STEPS[0].text);
  act(() => vi.advanceTimersByTime(6_000));
  expect(status.textContent).toContain(STEPS[1].text);
  expect(status.textContent).not.toContain(STEPS[0].text);
  act(() => vi.advanceTimersByTime(8_000));
  expect(status.textContent).toContain(STEPS[2].text);
  act(() => vi.advanceTimersByTime(11_000));
  expect(status.textContent).toContain(STEPS[3].text);
});
