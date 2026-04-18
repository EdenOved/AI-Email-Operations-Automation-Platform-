export function iso(ts: string): string {
  return new Date(ts).toISOString();
}

export function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}
