const timeFormatter = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", hour12: true });

const dateTimeFormatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeStyle: "short",
});

function parseDate(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** DD-MM-YYYY, as used throughout the design. */
export function formatDate(iso: string | null | undefined): string {
  const date = parseDate(iso);
  if (!date) return "NA";
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  return `${day}-${month}-${date.getFullYear()}`;
}

/** e.g. "9:47 AM". */
export function formatTime(iso: string | null | undefined): string {
  const date = parseDate(iso);
  return date ? timeFormatter.format(date) : "";
}

export function formatDateTime(iso: string | null | undefined): string {
  const date = parseDate(iso);
  return date ? dateTimeFormatter.format(date) : "—";
}

/**
 * Separates the country code from the subscriber number for display,
 * e.g. "+919876543210" -> "+91 9876543210". Other formats are shown as entered.
 */
export function formatPhone(phone: string): string {
  const compact = phone.replace(/[\s\-().]/g, "");
  const match = /^\+(\d{1,3})(\d{10})$/.exec(compact);
  return match ? `+${match[1]} ${match[2]}` : phone;
}

export function formatErrorCode(code: string): string {
  if (!code) return "";
  const label = code.replace(/_/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}
