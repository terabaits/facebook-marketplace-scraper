import { db } from '@/lib/db';
import { notFound } from 'next/navigation';
import { ScrapedActions } from './_components/scraped-actions';

export default async function ScrapedDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const item = await db.scrapedStory.findUnique({ where: { id }, include: { source: true } });
  if (!item) notFound();
  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">{item.title}</h1>
      <p className="text-text-secondary text-sm mb-4 font-mono">{item.source.name} · {item.url}</p>
      <ScrapedActions id={item.id} status={item.status} />
      <h2 className="text-lg font-bold mt-6 mb-2">Markdown saturs</h2>
      <pre className="bg-bg-subtle border border-border rounded p-4 font-mono text-xs whitespace-pre-wrap max-h-96 overflow-auto">{item.markdown}</pre>
    </div>
  );
}
