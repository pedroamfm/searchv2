export function formatFileSize(bytes: number): string {
  const units = ["B", "KB", "MB", "GB"];
  const exponent =
    bytes > 0
      ? Math.min(Math.floor(Math.log10(bytes) / 3), units.length - 1)
      : 0;
  return `${new Intl.NumberFormat("es-CL", { maximumFractionDigits: 1 }).format(bytes / 1000 ** exponent)} ${units[exponent]}`;
}

// This is a calendar date embedded in the filename, never a generation timestamp.
export function reportFileDate(filename: string): string | null {
  const match = /^product_radar_MLC_(\d{4})(\d{2})(\d{2})_/.exec(filename);
  if (!match) return null;
  const iso = `${match[1]}-${match[2]}-${match[3]}`;
  const date = new Date(`${iso}T12:00:00Z`);
  if (Number.isNaN(date.valueOf()) || date.toISOString().slice(0, 10) !== iso)
    return null;
  return new Intl.DateTimeFormat("es-CL", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}
