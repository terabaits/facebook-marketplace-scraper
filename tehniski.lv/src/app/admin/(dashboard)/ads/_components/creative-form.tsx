'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function CreativeForm({ slotId }: { slotId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [kind, setKind] = useState<'image' | 'embed'>('image');
  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const fd = new FormData(e.currentTarget);
    const data = {
      slot_id: slotId, kind,
      image_url: kind === 'image' ? fd.get('image_url') || null : null,
      target_url: kind === 'image' ? fd.get('target_url') || null : null,
      alt_text: kind === 'image' ? fd.get('alt_text') || null : null,
      embed_html: kind === 'embed' ? fd.get('embed_html') || null : null,
      weight: Number(fd.get('weight')) || 1,
      active: true
    };
    const res = await fetch('/api/admin/ads/creatives', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (res.ok) { (e.target as HTMLFormElement).reset(); router.refresh(); }
    setBusy(false);
  }
  return (
    <form onSubmit={handleSubmit} className="space-y-2 bg-bg-elevated border border-border rounded-md p-4">
      <div className="flex gap-2">
        <label className="flex items-center gap-1 text-sm"><input type="radio" checked={kind === 'image'} onChange={() => setKind('image')} /> Attēls</label>
        <label className="flex items-center gap-1 text-sm"><input type="radio" checked={kind === 'embed'} onChange={() => setKind('embed')} /> Embed HTML</label>
      </div>
      {kind === 'image' ? (
        <>
          <input name="image_url" placeholder="Attēla URL" className="w-full bg-bg-base border border-border rounded px-2 py-1 text-sm" />
          <input name="target_url" placeholder="Mērķa URL" className="w-full bg-bg-base border border-border rounded px-2 py-1 text-sm" />
          <input name="alt_text" placeholder="Alt teksts" className="w-full bg-bg-base border border-border rounded px-2 py-1 text-sm" />
        </>
      ) : (
        <textarea name="embed_html" placeholder="<script>...</script>" rows={4} className="w-full font-mono text-xs bg-bg-base border border-border rounded px-2 py-1" />
      )}
      <input name="weight" type="number" min={1} defaultValue={1} placeholder="Svars" className="w-24 bg-bg-base border border-border rounded px-2 py-1 text-sm" />
      <button type="submit" disabled={busy} className="bg-accent-primary text-bg-base font-bold px-3 py-1 rounded text-sm">{busy ? 'Pievieno...' : 'Pievienot'}</button>
    </form>
  );
}
