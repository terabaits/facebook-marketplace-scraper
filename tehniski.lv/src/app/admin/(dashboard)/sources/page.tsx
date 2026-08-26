import { db } from '@/lib/db';
import Link from 'next/link';
import { formatRelativeLv } from '@/lib/format';

export default async function SourcesPage() {
  const sources = await db.rssSource.findMany({ orderBy: { name: 'asc' } });
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">RSS avoti</h1>
        <Link
          href="/admin/sources/new"
          className="bg-accent-primary text-bg-base font-bold px-4 py-2 rounded-md"
        >
          Pievienot avotu
        </Link>
      </div>
      <table className="w-full text-sm">
        <thead className="text-left text-text-secondary border-b border-border">
          <tr>
            <th className="py-2">Nosaukums</th>
            <th>Statuss</th>
            <th>Pēdējais scrape</th>
            <th>Kļūda</th>
            <th>Skaits</th>
          </tr>
        </thead>
        <tbody>
          {sources.map((s) => (
            <tr key={s.id} className="border-b border-border hover:bg-bg-subtle">
              <td className="py-2">
                <Link href={`/admin/sources/${s.id}`} className="hover:text-accent-primary">
                  {s.name}
                </Link>
              </td>
              <td>
                {s.active ? (
                  <span className="text-success">aktīvs</span>
                ) : (
                  <span className="text-text-secondary">neaktīvs</span>
                )}
              </td>
              <td className="font-mono text-xs">
                {s.last_fetched_at ? formatRelativeLv(s.last_fetched_at) : '—'}
              </td>
              <td className="text-xs text-danger truncate max-w-xs">{s.last_error ?? '—'}</td>
              <td className="font-mono">{s.scrape_count}</td>
            </tr>
          ))}
          {sources.length === 0 && (
            <tr>
              <td colSpan={5} className="py-6 text-center text-text-secondary">
                Nav neviena RSS avota
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
