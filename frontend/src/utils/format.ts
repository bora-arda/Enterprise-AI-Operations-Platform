const currencyFormatters = new Map<string, Intl.NumberFormat>();

function currencyFormatter(currency: string): Intl.NumberFormat {
  const normalized = currency.toUpperCase();
  const existing = currencyFormatters.get(normalized);
  if (existing) return existing;
  const formatter = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: normalized,
    maximumFractionDigits: 0,
  });
  currencyFormatters.set(normalized, formatter);
  return formatter;
}

const dateFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
});

const dateTimeFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
});

const timeFormatter = new Intl.DateTimeFormat('en-US', {
  hour: 'numeric',
  minute: '2-digit',
});

const longDateFormatter = new Intl.DateTimeFormat('en-US', {
  weekday: 'long',
  month: 'long',
  day: 'numeric',
});

export function formatCurrency(amount: number, currency = 'GBP'): string {
  try {
    return currencyFormatter(currency).format(amount);
  } catch {
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 0,
    }).format(amount);
  }
}

export function formatDate(value: string): string {
  return dateFormatter.format(new Date(value));
}

export function formatDateTime(value: string): string {
  return dateTimeFormatter.format(new Date(value));
}

export function formatTime(value: string): string {
  return timeFormatter.format(new Date(value));
}

export function formatLongDate(value = new Date()): string {
  return longDateFormatter.format(value);
}

/** Compact relative age, e.g. "2h ago", "3d ago". */
export function relativeTime(value: string): string {
  const then = new Date(value).getTime();
  const diffSeconds = Math.round((then - Date.now()) / 1000);
  const abs = Math.abs(diffSeconds);

  const formatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });

  if (abs < 60) {
    return 'just now';
  }
  if (abs < 3600) {
    return formatter.format(Math.round(diffSeconds / 60), 'minute');
  }
  if (abs < 86400) {
    return formatter.format(Math.round(diffSeconds / 3600), 'hour');
  }
  if (abs < 604800) {
    return formatter.format(Math.round(diffSeconds / 86400), 'day');
  }
  return formatDate(value);
}

export function greetingForNow(now = new Date()): string {
  const hour = now.getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

export function initialsFromName(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
}
