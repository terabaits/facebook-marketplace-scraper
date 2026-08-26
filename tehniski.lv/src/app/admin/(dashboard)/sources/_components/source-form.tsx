'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function SourceForm({ source }: { source?: any }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [kind, setKind] = useState<'readability' | 'playwright'>(
    source?.parser_config?.kind ?? 'readability'
  );

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const fd = new FormData(e.currentTarget);
    const data = {
      name: fd.get('name'),
      feed_url: fd.get('feed_url'),
      site_url: fd.get('site_url'),
      active: fd.get('active') === 'on',
      parser_config: { kind }
    };
    const url = source ? `/api/admin/sources/${source.id}` : '/api/admin/sources';
    const method = source ? 'PATCH' : 'POST';
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (res.ok) {
      router.push('/admin/sources');
      router.refresh();
    } else {
      const e = await res.json().catch(() => ({}));
      setError(e.error ?? 'Kļūda');
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 max-w-2xl mt-6">
      <input
        name="name"
        defaultValue={source?.name}
        placeholder="Nosaukums"
        required
        className="w-full bg-bg-elevated border border-border rounded-md px-3 py-2"
      />
      <input
        name="feed_url"
        defaultValue={source?.feed_url}
        placeholder="Feed URL"
        required
        type="url"
        className="w-full bg-bg-elevated border border-border rounded-md px-3 py-2 font-mono text-sm"
      />
      <input
        name="site_url"
        defaultValue={source?.site_url}
        placeholder="Site URL"
        required
        type="url"
        className="w-full bg-bg-elevated border border-border rounded-md px-3 py-2 font-mono text-sm"
      />
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" name="active" defaultChecked={source?.active ?? true} /> Aktīvs
      </label>
      <div>
        <label className="block text-sm mb-1">Parsētājs</label>
        <div className="flex gap-4 text-sm">
          <label className="flex items-center gap-1">
            <input
              type="radio"
              checked={kind === 'readability'}
              onChange={() => setKind('readability')}
            />{' '}
            Readability (cheerio, ātrs)
          </label>
          <label className="flex items-center gap-1">
            <input
              type="radio"
              checked={kind === 'playwright'}
              onChange={() => setKind('playwright')}
            />{' '}
            Playwright (lēns, JS renderēts)
          </label>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={busy}
          className="bg-accent-primary text-bg-base font-bold px-4 py-2 rounded disabled:opacity-50"
        >
          {busy ? 'Saglabā...' : 'Saglabāt'}
        </button>
        {error && <span className="text-sm text-danger">{error}</span>}
      </div>
    </form>
  );
}
