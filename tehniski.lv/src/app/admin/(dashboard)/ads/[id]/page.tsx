import { db } from '@/lib/db';
import { notFound } from 'next/navigation';
import { CreativeForm } from '../_components/creative-form';

export default async function EditAdSlotPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const slot = await db.adSlot.findUnique({ where: { id }, include: { creatives: { orderBy: { created_at: 'desc' } } } });
  if (!slot) notFound();
  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">{slot.name}</h1>
      <p className="text-text-secondary text-sm mb-6 font-mono">{slot.key} · {slot.width}×{slot.height}</p>
      <h2 className="text-lg font-bold mb-3">Pievienot reklāmu</h2>
      <CreativeForm slotId={slot.id} />
      <h2 className="text-lg font-bold mt-8 mb-3">Esošās reklāmas ({slot.creatives.length})</h2>
      <div className="space-y-2">
        {slot.creatives.map(c => (
          <div key={c.id} className="bg-bg-elevated border border-border rounded-md p-3 text-sm">
            <div className="flex justify-between">
              <span className="font-mono">{c.kind} · {c.active ? 'aktīva' : 'neaktīva'}</span>
              <span className="text-text-secondary text-xs">{c.impressions} parādīšanas · {c.clicks} klikšķi</span>
            </div>
            {c.image_url && <div className="mt-1 text-xs text-text-secondary">→ {c.target_url}</div>}
            {c.embed_html && <div className="mt-1 text-xs text-text-secondary font-mono truncate">[embed HTML, {c.embed_html.length} chars]</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
