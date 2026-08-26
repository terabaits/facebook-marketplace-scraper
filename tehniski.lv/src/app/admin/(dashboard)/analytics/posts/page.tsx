import { db } from '@/lib/db';
import Link from 'next/link';

export default async function TopPostsPage({ searchParams }: { searchParams: Promise<{ range?: string }> }) {
  const sp = await searchParams;
  const range = sp.range ?? '7d';
  const days = range === '30d' ? 30 : range === 'all' ? 9999 : 7;
  const since = new Date(Date.now() - days * 86400000);
  const top = await db.$queryRaw<Array<{ id: string; slug: string; title: string; views: number }>>`
    SELECT p.id, p.slug, p.title, COUNT(v.id)::int AS views
    FROM "Post" p
    LEFT JOIN "PostView" v ON v.post_id = p.id AND v.occurred_at >= ${since}
    WHERE p.status = 'published' AND p.deleted_at IS NULL
    GROUP BY p.id
    ORDER BY views DESC
    LIMIT 20
  `;
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Populārākie raksti</h1>
      <div className="flex gap-2 mb-4 text-sm">
        <Link href="/admin/analytics/posts?range=7d" className={range === '7d' ? 'font-bold' : ''}>7 dienas</Link>
        <Link href="/admin/analytics/posts?range=30d" className={range === '30d' ? 'font-bold' : ''}>30 dienas</Link>
        <Link href="/admin/analytics/posts?range=all" className={range === 'all' ? 'font-bold' : ''}>Visi laiki</Link>
      </div>
      <table className="w-full text-sm">
        <thead className="text-left border-b border-border text-text-secondary">
          <tr><th className="py-2">Raksts</th><th>Skatījumi</th></tr>
        </thead>
        <tbody>
          {top.map(p => (
            <tr key={p.id} className="border-b border-border">
              <td className="py-2"><Link href={`/post/${p.slug}`} target="_blank" className="hover:text-accent-primary">{p.title}</Link></td>
              <td className="font-mono">{p.views}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
