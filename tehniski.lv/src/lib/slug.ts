export function diacriticFold(s: string): string {
  return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

export function slugify(input: string): string {
  return input
    .normalize('NFC')
    .toLowerCase()
    .replace(/[^a-zāčēģīķļņšūž0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .slice(0, 80)
    .replace(/^-|-$/g, '');
}
