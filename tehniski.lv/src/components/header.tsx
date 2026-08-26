import Link from 'next/link';
import { Wordmark } from './wordmark';
import { ThemeToggle } from './theme-toggle';

export function Header() {
  return (
    <header className="border-b border-border bg-bg-elevated">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        <Wordmark />
        <nav className="flex items-center gap-6 text-sm">
          <Link href="/" className="hover:text-accent-primary">Jaunumi</Link>
          <Link href="/category/ai" className="hover:text-accent-primary">Kategorijas</Link>
          <Link href="/search" className="hover:text-accent-primary">Meklēt</Link>
          <Link href="/about" className="hover:text-accent-primary">Par mums</Link>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
