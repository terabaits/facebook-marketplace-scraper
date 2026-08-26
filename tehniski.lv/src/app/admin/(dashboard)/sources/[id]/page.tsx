import { db } from '@/lib/db';
import { notFound } from 'next/navigation';
import { SourceForm } from '../_components/source-form';
import { FetchNowButton } from '../_components/fetch-now-button';

export default async function EditSourcePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const source = await db.rssSource.findUnique({ where: { id } });
  if (!source) notFound();
  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">{source.name}</h1>
      <p className="text-text-secondary text-sm mb-4 font-mono">{source.feed_url}</p>
      <FetchNowButton sourceId={source.id} />
      <SourceForm source={source} />
    </div>
  );
}
