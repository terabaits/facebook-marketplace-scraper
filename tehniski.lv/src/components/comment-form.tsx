'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function CommentForm({ postId, parentId, onSuccess }: { postId: string; parentId?: string; onSuccess?: () => void }) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    const fd = new FormData(e.currentTarget);
    const res = await fetch('/api/comments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        post_id: postId, parent_id: parentId ?? null,
        author_name: fd.get('author_name'), author_email: fd.get('author_email'),
        body: fd.get('body')
      })
    });
    setSubmitting(false);
    if (res.ok) {
      setMessage('Jūsu komentārs gaida apstiprinājumu.');
      (e.target as HTMLFormElement).reset();
      onSuccess?.();
      router.refresh();
    } else {
      const data = await res.json().catch(() => ({}));
      setMessage(data.error ?? 'Kļūda');
    }
  }
  return (
    <form onSubmit={handleSubmit} className="space-y-2 mb-6">
      <div className="grid grid-cols-2 gap-2">
        <input name="author_name" placeholder="Vārds" required maxLength={80} className="bg-bg-elevated border border-border rounded px-3 py-2 text-sm" />
        <input name="author_email" type="email" placeholder="E-pasts (netiks publicēts)" required maxLength={200} className="bg-bg-elevated border border-border rounded px-3 py-2 text-sm" />
      </div>
      <textarea name="body" placeholder="Jūsu komentārs..." required maxLength={5000} rows={3} className="w-full bg-bg-elevated border border-border rounded px-3 py-2 text-sm" />
      <div className="flex items-center gap-3">
        <button type="submit" disabled={submitting} className="bg-accent-primary text-bg-base font-bold px-3 py-1 rounded text-sm">
          {submitting ? 'Sūta...' : 'Iesniegt'}
        </button>
        {message && <span className="text-xs text-text-secondary">{message}</span>}
      </div>
    </form>
  );
}
