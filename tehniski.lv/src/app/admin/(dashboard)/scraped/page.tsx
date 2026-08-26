import { db } from '@/lib/db';
import Link from 'next/link';
import { formatRelativeLv } from '@/lib/format';

export default async function ScrapedListPage({ searchParams }: { searchParams: Promise<{ status?: string; source_id?: string }> }) {
  const sp = await searchParams;
  const where: any = {};
  if (sp.status) where.status = sp.status;
  if (sp.source_id) where.source_id = sp.source_id;
  const items = await db.scrapedStory.findMany({ where, orderBy: { scraped_at: 'desc' }, take: 100, include: { source: { select: { name: true } } } });
  const sources = await db.rssSource.findMany({ orderBy: { name: 'asc' }, select: { id: true, name: true } });
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Stāsti (scraped)</h1>
      <div className="flex gap-2 mb-4 text-sm flex-wrap">
        <Link href="/admin/scraped" className={!sp.status ? 'font-bold' : ''}>Visi</Link>
        <Link href="/admin/scraped?status=new" className={sp.status === 'new' ? 'font-bold' : ''}>Jauni</Link>
        <Link href="/admin/scraped?status=used" className={sp.status === 'used' ? 'font-bold' : ''}>Izmantoti</Link>
        <Link href="/admin/scraped?status=ignored" className={sp.status === 'ignored' ? 'font-bold' : ''}>Ignorēti</Link>
        <span className="mx-2 text-text-secondary">|</span>
        {sources.map(s => <Link key={s.id} href={`/admin/scraped?source_id=${s.id}`} className={sp.source_id === s.id ? 'font-bold' : ''}>{s.name}</Link>)}
      </div>
      <div className="space-y-2">
        {items.map(it => (
          <Link key={it.id} href={`/admin/scraped/${it.id}`} className="block bg-bg-elevated border border-border rounded-md p-3 hover:border-accent-primary">
            <div className="flex justify-between">
              <div className="font-bold">{it.title}</div>
              <div className="text-xs text-text-secondary font-mono">{it.source.name} · {formatRelativeLv(it.scraped_at)}</div>
            </div>
            <p className="text-sm text-text-secondary mt-1 line-clamp-2">{it.summary}</p>
            <div className="text-xs text-text-secondary font-mono mt-1">{it.url} · {it.word_count ?? '?'} vārdi · {it.status}</div>
          </Link>
        ))}
        {items.length === 0 && (
          <div className="text-center text-text-secondary py-6">Nav neviena stāsta</div>
        )}
      </div>
    </div>
  );
}
