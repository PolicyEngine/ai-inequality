import "@testing-library/jest-dom";

class ResizeObserver {
  observe() {}

  unobserve() {}

  disconnect() {}
}

if (!window.ResizeObserver) {
  window.ResizeObserver = ResizeObserver;
}
