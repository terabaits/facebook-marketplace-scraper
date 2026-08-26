import { db } from '@/lib/db';
import Link from 'next/link';
import { formatDateLv } from '@/lib/format';

export default async function NewsletterListPage() {
  const runs = await db.newsletterRun.findMany({
    orderBy: { target_date: 'desc' },
    take: 30,
    include: { _count: { select: { selections: true, posts: true } } }
  });
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Newsletter</h1>
        <Link
          href="/admin/newsletter/new"
          className="bg-accent-primary text-bg-base font-bold px-4 py-2 rounded-md"
        >
          Jauns izdevums
        </Link>
      </div>
      <table className="w-full text-sm">
        <thead className="text-left text-text-secondary border-b border-border">
          <tr>
            <th className="py-2">Datums</th>
            <th>Statuss</th>
            <th>Stāsti</th>
            <th>Raksti</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr key={r.id} className="border-b border-border hover:bg-bg-subtle">
              <td className="py-2">
                <Link href={`/admin/newsletter/${r.id}`} className="hover:text-accent-primary font-mono">
                  {formatDateLv(r.target_date)}
                </Link>
              </td>
              <td className="font-mono text-xs">{r.status}</td>
              <td className="font-mono">{r._count.selections}</td>
              <td className="font-mono">{r._count.posts}</td>
            </tr>
          ))}
          {runs.length === 0 && (
            <tr>
              <td colSpan={4} className="py-6 text-center text-text-secondary">
                Nav neviena newsletter izdevuma
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
