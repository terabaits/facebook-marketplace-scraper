import { db } from '@/lib/db';
import Link from 'next/link';

export default async function PromptsPage() {
  const prompts = await db.promptTemplate.findMany({ orderBy: [{ key: 'asc' }, { version: 'desc' }] });
  // Group by key
  const grouped = new Map<string, typeof prompts>();
  for (const p of prompts) {
    if (!grouped.has(p.key)) grouped.set(p.key, []);
    grouped.get(p.key)!.push(p);
  }
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Prompt veidnes</h1>
      <div className="space-y-6">
        {Array.from(grouped.entries()).map(([key, versions]) => (
          <div key={key} className="bg-bg-elevated border border-border rounded-md p-4">
            <div className="flex justify-between items-start mb-2">
              <div>
                <h2 className="font-bold text-lg">{versions[0].name}</h2>
                <p className="text-sm text-text-secondary">{versions[0].description}</p>
                <p className="text-xs text-text-secondary font-mono mt-1">key: {key} · {versions.length} versija{versions.length === 1 ? '' : 's'}</p>
              </div>
              <Link href={`/admin/prompts/${key}`} className="text-accent-primary hover:underline text-sm">Rediģēt</Link>
            </div>
            <div className="flex gap-2 text-xs">
              {versions.map(v => (
                <span key={v.id} className={`px-2 py-0.5 rounded font-mono ${v.active ? 'bg-success text-bg-base' : 'bg-bg-subtle text-text-secondary'}`}>
                  v{v.version}{v.active ? ' • aktīvs' : ''}
                </span>
              ))}
            </div>
          </div>
        ))}
        {grouped.size === 0 && (
          <div className="text-center text-text-secondary py-6">Nav nevienas prompt veidnes</div>
        )}
      </div>
    </div>
  );
}
