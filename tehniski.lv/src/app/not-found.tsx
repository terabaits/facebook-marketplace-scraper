import Link from 'next/link';
import { Search } from 'lucide-react';
import { lv } from '@/lib/lv';

export default function NotFound() {
  return (
    <div className="max-w-md mx-auto py-16 text-center">
      <p className="font-mono text-6xl text-text-secondary mb-2" aria-hidden>404</p>
      <h1 className="text-2xl font-bold mb-3">{lv.notFound.title}</h1>
      <p className="text-text-secondary mb-6">{lv.notFound.lead}</p>

      <form method="get" action="/search" className="mb-6" role="search">
        <label htmlFor="nf-q" className="sr-only">{lv.search.searchOnSite}</label>
        <div className="flex items-center gap-2 bg-bg-elevated border border-border rounded-md px-3 py-2">
          <Search size={16} className="text-text-secondary" aria-hidden />
          <input
            id="nf-q"
            name="q"
            type="search"
            placeholder={lv.search.placeholder}
            aria-label={lv.search.searchOnSite}
            className="bg-transparent flex-1 outline-none text-sm"
          />
        </div>
      </form>

      <Link
        href="/"
        className="inline-block bg-accent-primary text-bg-base px-4 py-2 rounded-md hover:opacity-90"
      >
        ← {lv.notFound.cta}
      </Link>
    </div>
  );
}
