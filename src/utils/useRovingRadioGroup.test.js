import React, { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import { useRovingRadioGroup } from "./useRovingRadioGroup";

const OPTIONS = ["alpha", "beta", "gamma"];

function Harness({ initial = "alpha" }) {
  const [selected, setSelected] = useState(initial);
  const nav = useRovingRadioGroup(OPTIONS, selected);
  return (
    <div role="radiogroup" aria-label="Harness">
      {OPTIONS.map((key) => (
        <button
          key={key}
          ref={nav.getRef(key)}
          type="button"
          role="radio"
          aria-checked={selected === key}
          tabIndex={selected === key ? 0 : -1}
          onClick={() => setSelected(key)}
          onKeyDown={nav.keyDownHandler(setSelected)}
        >
          {key}
        </button>
      ))}
    </div>
  );
}

test("arrow keys cycle forward through options and move focus", () => {
  render(<Harness />);
  const alpha = screen.getByRole("radio", { name: "alpha" });
  const beta = screen.getByRole("radio", { name: "beta" });
  const gamma = screen.getByRole("radio", { name: "gamma" });

  expect(alpha).toHaveAttribute("tabindex", "0");
  expect(beta).toHaveAttribute("tabindex", "-1");

  alpha.focus();
  fireEvent.keyDown(alpha, { key: "ArrowRight" });
  expect(beta).toHaveAttribute("aria-checked", "true");
  expect(beta).toHaveAttribute("tabindex", "0");
  expect(document.activeElement).toBe(beta);

  fireEvent.keyDown(beta, { key: "ArrowDown" });
  expect(gamma).toHaveAttribute("aria-checked", "true");
  expect(document.activeElement).toBe(gamma);

  // wraps to first
  fireEvent.keyDown(gamma, { key: "ArrowRight" });
  expect(alpha).toHaveAttribute("aria-checked", "true");
  expect(document.activeElement).toBe(alpha);
});

test("arrow keys cycle backward and wrap", () => {
  render(<Harness />);
  const alpha = screen.getByRole("radio", { name: "alpha" });
  const gamma = screen.getByRole("radio", { name: "gamma" });

  alpha.focus();
  fireEvent.keyDown(alpha, { key: "ArrowLeft" });
  expect(gamma).toHaveAttribute("aria-checked", "true");
  expect(document.activeElement).toBe(gamma);

  fireEvent.keyDown(gamma, { key: "ArrowUp" });
  expect(screen.getByRole("radio", { name: "beta" })).toHaveAttribute(
    "aria-checked",
    "true",
  );
});

test("Home and End jump to first and last option", () => {
  render(<Harness initial="beta" />);
  const alpha = screen.getByRole("radio", { name: "alpha" });
  const beta = screen.getByRole("radio", { name: "beta" });
  const gamma = screen.getByRole("radio", { name: "gamma" });

  beta.focus();
  fireEvent.keyDown(beta, { key: "End" });
  expect(gamma).toHaveAttribute("aria-checked", "true");
  expect(document.activeElement).toBe(gamma);

  fireEvent.keyDown(gamma, { key: "Home" });
  expect(alpha).toHaveAttribute("aria-checked", "true");
  expect(document.activeElement).toBe(alpha);
});

test("ignores unrelated keys", () => {
  render(<Harness />);
  const alpha = screen.getByRole("radio", { name: "alpha" });
  alpha.focus();
  fireEvent.keyDown(alpha, { key: "Tab" });
  expect(alpha).toHaveAttribute("aria-checked", "true");
  expect(document.activeElement).toBe(alpha);
});
