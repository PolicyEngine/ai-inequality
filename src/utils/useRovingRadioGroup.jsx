import { useCallback, useRef } from "react";

/**
 * Keyboard-accessible roving tabindex helper for button-based radiogroups.
 *
 * Returns a `getRef` factory to attach to each radio button, and a `keyDownHandler`
 * factory that wires ArrowLeft/Right/Up/Down/Home/End to cycle the selection and
 * move focus to match (per the WAI-ARIA radiogroup pattern).
 *
 * Usage:
 *   const nav = useRovingRadioGroup(options, selected);
 *   ...
 *   <button
 *     ref={nav.getRef(key)}
 *     role="radio"
 *     aria-checked={selected === key}
 *     tabIndex={selected === key ? 0 : -1}
 *     onKeyDown={nav.keyDownHandler(setSelected)}
 *     onClick={() => setSelected(key)}
 *   />
 */
export function useRovingRadioGroup(options, selected) {
  const refs = useRef({});

  const getRef = useCallback(
    (key) => (element) => {
      if (element) {
        refs.current[key] = element;
      } else {
        delete refs.current[key];
      }
    },
    [],
  );

  const keyDownHandler = useCallback(
    (setSelected) => (event) => {
      const currentIdx = options.indexOf(selected);
      if (currentIdx === -1) return;

      let nextIdx;
      switch (event.key) {
        case "ArrowRight":
        case "ArrowDown":
          nextIdx = (currentIdx + 1) % options.length;
          break;
        case "ArrowLeft":
        case "ArrowUp":
          nextIdx = (currentIdx - 1 + options.length) % options.length;
          break;
        case "Home":
          nextIdx = 0;
          break;
        case "End":
          nextIdx = options.length - 1;
          break;
        default:
          return;
      }

      event.preventDefault();
      const nextKey = options[nextIdx];
      setSelected(nextKey);
      // Focus the newly selected radio so keyboard users see where they are.
      const nextEl = refs.current[nextKey];
      if (nextEl && typeof nextEl.focus === "function") {
        nextEl.focus();
      }
    },
    [options, selected],
  );

  return { getRef, keyDownHandler };
}
