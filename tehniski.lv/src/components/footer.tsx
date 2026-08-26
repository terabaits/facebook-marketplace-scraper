import Link from 'next/link';

export function Footer() {
  return (
    <footer className="border-t border-border bg-bg-elevated mt-16 py-8">
      <div className="max-w-6xl mx-auto px-4 text-sm text-text-secondary">
        <div>© 2026 tehniski.lv</div>
        <div className="mt-4 flex gap-4">
          <Link href="/about">Par mums</Link>
          <Link href="/privacy">Privātums</Link>
          <Link href="/contact">Kontakti</Link>
        </div>
      </div>
    </footer>
  );
}
