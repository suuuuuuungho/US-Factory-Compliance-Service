// SUU-193: dockview는 ResizeObserver가 필요한데 jsdom에는 없다. 아무것도 안 하는 가짜를 넣는다.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
