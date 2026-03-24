export interface RingConfig {
  label: string;
  min: number;
  max: number;
  step: number;
}

/**
 * Validate a grind display string against ring configuration.
 * Returns error message or null if valid.
 */
export function validateGrindDisplay(
  input: string,
  rings: RingConfig[],
): string | null {
  if (!input.trim()) return null; // Empty is OK (optional field)

  const segments = input.split('.');
  if (segments.length !== rings.length) {
    return `Expected ${rings.length} segment${rings.length > 1 ? 's' : ''} (${rings.map((r) => r.label).join('.')})`;
  }

  for (let i = 0; i < segments.length; i++) {
    const num = Number(segments[i]);
    const ring = rings[i];
    if (Number.isNaN(num)) {
      return `${ring.label}: must be a number`;
    }
    if (num < ring.min || num > ring.max) {
      return `${ring.label}: must be ${ring.min}-${ring.max}`;
    }
    if (ring.step > 0 && (num - ring.min) % ring.step !== 0) {
      return `${ring.label}: must be in steps of ${ring.step}`;
    }
  }
  return null;
}

/**
 * Get display range string, e.g. "0.0.0 — 4.9.5" or "0 — 40"
 */
export function getGrindRangeDisplay(rings: RingConfig[]): string {
  const minParts = rings.map((r) => String(r.min));
  const maxParts = rings.map((r) => String(r.max));
  return `${minParts.join('.')} — ${maxParts.join('.')}`;
}

/**
 * Get placeholder string, e.g. "e.g. 2.3.4" or "e.g. 22"
 */
export function getGrindPlaceholder(rings: RingConfig[]): string {
  const midParts = rings.map((r) => String(Math.floor((r.min + r.max) / 2)));
  return `e.g. ${midParts.join('.')}`;
}
