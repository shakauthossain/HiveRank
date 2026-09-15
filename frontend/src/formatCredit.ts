/** Format DataForSEO credit (USD) for tables. */
export function formatCredit(value?: number | null): string {
  if (value == null || Number.isNaN(Number(value)) || Number(value) <= 0) {
    return "—";
  }
  return `$${Number(value).toFixed(4)}`;
}
