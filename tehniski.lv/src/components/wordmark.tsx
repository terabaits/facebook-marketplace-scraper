import Link from 'next/link';

export function Wordmark() {
  return (
    <Link href="/" className="flex items-center gap-1 font-mono font-bold text-lg">
      <span>tehniski.lv</span>
      <span className="inline-block w-2 h-4 bg-accent-primary animate-pulse" aria-hidden />
    </Link>
  );
}
