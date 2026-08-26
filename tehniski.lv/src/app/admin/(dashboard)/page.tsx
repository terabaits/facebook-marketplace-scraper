import { db } from '@/lib/db';
import Link from 'next/link';
import { formatRelativeLv } from '@/lib/format';

export default async function Dashboard() {
  const [posts, comments, sources, scraped, ads, heartbeat] = await Promise.all([
    db.post.groupBy({ by: ['status'], _count: true }),
    db.comment.count({ where: { status: 'pending' } }),
    db.rssSource.count(),
    db.scrapedStory.count(),
    db.adCreative.count({ where: { active: true } }),
    db.workerHeartbeat.findUnique({ where: { id: 'singleton' } }).catch(() => null)
  ]);
  const ageSeconds = heartbeat ? Math.floor((Date.now() - heartbeat.last_seen.getTime()) / 1000) : null;
  const status: { label: string; color: string } =
    ageSeconds === null
      ? { label: 'Worker: stopped', color: 'bg-danger/20 text-danger border-danger' }
      : ageSeconds < 300
      ? { label: `Worker: active ${formatRelativeLv(heartbeat!.last_seen)}`, color: 'bg-success/20 text-success border-success' }
      : ageSeconds < 3600
      ? { label: `Worker: stale ${formatRelativeLv(heartbeat!.last_seen)}`, color: 'bg-warning/20 text-warning border-warning' }
      : { label: `Worker: stale ${formatRelativeLv(heartbeat!.last_seen)}`, color: 'bg-danger/20 text-danger border-danger' };
  const card = (label: string, value: number, href: string) => (
    <Link href={href} className="block bg-bg-elevated border border-border rounded-md p-4 hover:border-accent-primary">
      <div className="text-3xl font-bold">{value}</div>
      <div className="text-text-secondary text-sm">{label}</div>
    </Link>
  );
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Panelis</h1>
      <div className={`inline-block border rounded-md px-3 py-1 text-xs font-mono mb-4 ${status.color}`}>
        {status.label}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {card('Publicētie', posts.find(p => p.status === 'published')?._count ?? 0, '/admin/posts')}
        {card('Melnraksti', posts.find(p => p.status === 'draft')?._count ?? 0, '/admin/posts')}
        {card('Gaida komentāri', comments, '/admin/comments')}
        {card('Aktīvās reklāmas', ads, '/admin/ads')}
      </div>
    </div>
  );
}
