export function snap125(value) {
  if (value <= 0 || !Number.isFinite(value)) return 1;

  const exponent = Math.floor(Math.log10(value));
  const scale = 10 ** exponent;
  const normalized = value / scale;

  if (normalized <= 1) return scale;
  if (normalized <= 2) return 2 * scale;
  if (normalized <= 5) return 5 * scale;
  return 10 * scale;
}

export function niceTicks(min, max, targetCount = 5) {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [0];
  if (min === max) return [min];

  const low = Math.min(min, max);
  const high = Math.max(min, max);
  const roughStep = Math.abs(high - low) / Math.max(targetCount - 1, 1);
  const step = snap125(roughStep);
  const start = Math.floor(low / step) * step;
  const stop = Math.ceil(high / step) * step;
  const ticks = [];

  for (let value = start; value <= stop + step * 0.5; value += step) {
    ticks.push(Number(value.toFixed(12)));
  }

  return ticks;
}
