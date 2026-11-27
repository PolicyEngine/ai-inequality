import "@testing-library/jest-dom";

class ResizeObserver {
  observe() {}

  unobserve() {}

  disconnect() {}
}

// Node-environment tests, such as the head-tag tests, have no window.
if (typeof window !== "undefined" && !window.ResizeObserver) {
  window.ResizeObserver = ResizeObserver;
}
