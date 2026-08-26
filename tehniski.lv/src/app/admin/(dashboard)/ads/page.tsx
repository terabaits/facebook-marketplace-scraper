import { db } from '@/lib/db';
import Link from 'next/link';

export default async function AdsPage() {
  const slots = await db.adSlot.findMany({ orderBy: { name: 'asc' }, include: { _count: { select: { creatives: true } } } });
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Reklāmas</h1>
      <div className="space-y-3">
        {slots.map(s => (
          <Link key={s.id} href={`/admin/ads/${s.id}`} className="block bg-bg-elevated border border-border rounded-md p-4 hover:border-accent-primary">
            <div className="flex justify-between">
              <div>
                <div className="font-bold">{s.name}</div>
                <div className="text-xs text-text-secondary font-mono">{s.key} · {s.width}×{s.height}</div>
              </div>
              <div className="text-sm text-text-secondary">{s._count.creatives} reklāmas</div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
