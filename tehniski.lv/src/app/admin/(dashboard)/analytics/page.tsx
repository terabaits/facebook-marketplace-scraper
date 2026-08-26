import { db } from '@/lib/db';

export default async function AnalyticsPage() {
  const [posts, views, comments, searches, adImpressions, adClicks] = await Promise.all([
    db.post.count({ where: { status: 'published' } }),
    db.post.aggregate({ _sum: { view_count: true } }).then(r => r._sum.view_count ?? 0),
    db.comment.count({ where: { status: 'approved' } }),
    db.searchQuery.count({ where: { occurred_at: { gte: new Date(Date.now() - 7 * 86400000) } } }),
    db.adEvent.count({ where: { kind: 'impression' } }),
    db.adEvent.count({ where: { kind: 'click' } })
  ]);
  const ctr = adImpressions > 0 ? ((adClicks / adImpressions) * 100).toFixed(2) : '0';
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Analītika</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <Stat label="Publicētie raksti" value={posts} />
        <Stat label="Kopā skatījumi" value={views} />
        <Stat label="Komentāri (apstiprināti)" value={comments} />
        <Stat label="Meklēšana (7d)" value={searches} />
        <Stat label="Reklāmu parādīšanas" value={adImpressions} />
        <Stat label="Reklāmu klikšķi" value={adClicks} />
        <Stat label="CTR" value={`${ctr}%`} />
      </div>
      <a href="/admin/analytics/posts" className="text-accent-primary hover:underline">Skatīt populārākos rakstus →</a>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-bg-elevated border border-border rounded-md p-4">
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-text-secondary">{label}</div>
    </div>
  );
}
