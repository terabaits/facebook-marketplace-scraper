'use client';
import { useState } from 'react';

export function CoverUpload({ name, defaultUrl }: { name: string; defaultUrl?: string }) {
  const [url, setUrl] = useState(defaultUrl ?? '');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await fetch('/api/admin/uploads/cover', { method: 'POST', body: form });
      if (res.ok) {
        const data = await res.json();
        setUrl(data.url);
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.error ?? 'Augšupielāde neizdevās');
      }
    } catch (err: any) {
      setError(err?.message ?? 'Augšupielāde neizdevās');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <input type="hidden" name={name} value={url} />
      <input
        type="file"
        accept="image/*"
        onChange={handleUpload}
        disabled={uploading}
        className="text-sm"
      />
      {uploading && <span className="ml-2 text-sm">Augšupielādē...</span>}
      {error && <span className="ml-2 text-sm text-danger">{error}</span>}
      {url && <img src={url} alt="" className="mt-2 max-w-xs rounded border border-border" />}
    </div>
  );
}
