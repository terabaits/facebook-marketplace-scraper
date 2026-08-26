'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function SettingsForm({ initial }: { initial: Record<string, string> }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true); setMessage(null);
    const fd = new FormData(e.currentTarget);
    const data: Record<string, string> = {};
    for (const [k, v] of fd.entries()) if (typeof v === 'string' && v) data[k] = v;
    const res = await fetch('/api/admin/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (res.ok) { setMessage('Saglabāts'); router.refresh(); }
    setBusy(false);
  }
  const Field = ({ k, label, type = 'text' }: { k: string; label: string; type?: string }) => (
    <div>
      <label className="block text-sm mb-1">{label}</label>
      <input name={k} type={type} defaultValue={initial[k] ?? ''} className="w-full bg-bg-elevated border border-border rounded px-3 py-2 text-sm" />
    </div>
  );
  return (
    <form onSubmit={handleSubmit} className="space-y-3 max-w-2xl">
      <Field k="site_name" label="Vietnes nosaukums" />
      <Field k="default_og_image_url" label="Noklusējuma OG attēls (URL)" type="url" />
      <div>
        <label className="block text-sm mb-1">Kājene (Markdown)</label>
        <textarea name="footer_markdown" defaultValue={initial['footer_markdown'] ?? ''} rows={4} className="w-full font-mono text-sm bg-bg-elevated border border-border rounded px-3 py-2" />
      </div>
      <Field k="contact_email" label="Kontakta e-pasts" type="email" />
      <Field k="social_twitter" label="Twitter/X URL" />
      <Field k="social_facebook" label="Facebook URL" />
      <Field k="social_linkedin" label="LinkedIn URL" />
      <div className="flex items-center gap-3">
        <button type="submit" disabled={busy} className="bg-accent-primary text-bg-base font-bold px-4 py-2 rounded">{busy ? 'Saglabā...' : 'Saglabāt'}</button>
        {message && <span className="text-sm text-text-secondary">{message}</span>}
      </div>
    </form>
  );
}
