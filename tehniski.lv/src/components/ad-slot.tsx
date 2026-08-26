import { getActiveCreatives } from '@/lib/ads-server';
import { db } from '@/lib/db';
import { headers } from 'next/headers';
import { createHash } from 'node:crypto';

export async function AdSlot({ slotKey }: { slotKey: string }) {
  const result = await getActiveCreatives(slotKey);
  if (!result) return <div className="bg-bg-subtle border border-border rounded p-4 text-center text-xs text-text-secondary">Reklāma</div>;
  const { creative } = result;
  if (!creative) return <div className="bg-bg-subtle border border-border rounded p-4 text-center text-xs text-text-secondary">Reklāma</div>;
  // Track impression (best-effort, don't block render)
  trackImpression(creative.id).catch(() => {});
  if (creative.kind === 'image' && creative.image_url && creative.target_url) {
    return (
      <a href={`/api/ads/track?creative_id=${creative.id}&kind=click&redirect=${encodeURIComponent(creative.target_url)}`} target="_blank" rel="noopener" className="block">
        <img src={creative.image_url} alt={creative.alt_text ?? ''} className="w-full rounded" />
      </a>
    );
  }
  if (creative.kind === 'embed' && creative.embed_html) {
    return <div dangerouslySetInnerHTML={{ __html: creative.embed_html }} />;
  }
  return null;
}

async function trackImpression(creativeId: string) {
  const h = await headers();
  const ip = h.get('x-forwarded-for') ?? '0.0.0.0';
  const ua = h.get('user-agent') ?? '';
  const ipHash = createHash('sha256').update(ip).digest('hex').slice(0, 32);
  await db.$transaction([
    db.adEvent.create({ data: { creative_id: creativeId, kind: 'impression', ip_hash: ipHash, user_agent: ua.slice(0, 256) } }),
    db.adCreative.update({ where: { id: creativeId }, data: { impressions: { increment: 1 } } })
  ]);
}
