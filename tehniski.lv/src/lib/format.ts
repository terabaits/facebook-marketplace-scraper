const TZ = 'Europe/Riga';
const fmt = new Intl.DateTimeFormat('lv-LV', { timeZone: TZ, day: '2-digit', month: '2-digit', year: 'numeric' });
const fmtTime = new Intl.DateTimeFormat('lv-LV', { timeZone: TZ, hour: '2-digit', minute: '2-digit', hour12: false });

export function formatDateLv(d: Date): string {
  const parts = fmt.formatToParts(d);
  const day = parts.find(p => p.type === 'day')!.value;
  const month = parts.find(p => p.type === 'month')!.value;
  const year = parts.find(p => p.type === 'year')!.value;
  return `${day}.${month}.${year}.`;
}

export function formatDateTimeLv(d: Date): string {
  return `${formatDateLv(d)} ${fmtTime.format(d)}`;
}

export function formatNumberLv(n: number): string {
  return new Intl.NumberFormat('lv-LV', { useGrouping: 'always' }).format(n);
}

function isSameDay(a: Date, b: Date): boolean {
  return formatDateLv(a) === formatDateLv(b);
}

function hoursBetween(a: Date, b: Date): number {
  return Math.floor((b.getTime() - a.getTime()) / 3_600_000);
}

export function formatRelativeLv(d: Date, now: Date = new Date()): string {
  if (isSameDay(d, now)) {
    const h = hoursBetween(d, now);
    if (h <= 0) return 'tagad';
    if (h === 1) return 'pirms 1 stundas';
    if (h < 4) return `pirms ${h} stundām`;
    return 'šodien';
  }
  const oneDay = 86_400_000;
  const dayBefore = new Date(now.getTime() - oneDay);
  if (isSameDay(d, dayBefore)) return 'vakar';
  return formatDateLv(d);
}
