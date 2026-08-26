'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { MarkdownEditor } from '@/components/markdown-editor';
import { CoverUpload } from '@/components/cover-upload';

type Category = { id: string; name: string };

export function PostForm({ categories, post }: { categories: Category[]; post?: any }) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const fd = new FormData(e.currentTarget);
    const data = {
      title: fd.get('title'),
      excerpt: fd.get('excerpt'),
      content_md: fd.get('content_md'),
      cover_image_url: fd.get('cover_image_url') || null,
      cover_image_alt: fd.get('cover_image_alt') || null,
      category_id: fd.get('category_id') || null,
      featured_tier: fd.get('featured_tier') || null
    };

    const url = post ? `/api/admin/posts/${post.id}` : '/api/admin/posts';
    const method = post ? 'PATCH' : 'POST';
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (res.ok) {
      router.push('/admin/posts');
      router.refresh();
    } else {
      const e = await res.json().catch(() => ({}));
      setError(e.error ?? 'Kļūda');
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <input
        name="title"
        defaultValue={post?.title}
        placeholder="Virsraksts"
        required
        className="w-full bg-bg-elevated border border-border rounded-md px-3 py-2 text-2xl font-bold"
      />
      <textarea
        name="excerpt"
        defaultValue={post?.excerpt}
        placeholder="Īss apraksts"
        required
        className="w-full bg-bg-elevated border border-border rounded-md px-3 py-2"
      />
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm mb-1">Vāka attēls</label>
          <CoverUpload name="cover_image_url" defaultUrl={post?.cover_image_url} />
        </div>
        <div>
          <label className="block text-sm mb-1">Vāka attēla alt teksts</label>
          <input
            name="cover_image_alt"
            defaultValue={post?.cover_image_alt}
            className="w-full bg-bg-elevated border border-border rounded-md px-3 py-2"
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <select
          name="category_id"
          defaultValue={post?.category_id ?? ''}
          className="bg-bg-elevated border border-border rounded-md px-3 py-2"
        >
          <option value="">Bez kategorijas</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          name="featured_tier"
          defaultValue={post?.featured_tier ?? ''}
          className="bg-bg-elevated border border-border rounded-md px-3 py-2"
        >
          <option value="">Nav izcelts</option>
          <option value="big">Lielais (2 virs)</option>
          <option value="medium">Vidējais (4 virs)</option>
        </select>
      </div>
      <MarkdownEditor name="content_md" defaultValue={post?.content_md ?? ''} />
      <div className="flex gap-3 items-center">
        <button
          type="submit"
          disabled={submitting}
          className="bg-accent-primary text-bg-base font-bold px-4 py-2 rounded-md disabled:opacity-50"
        >
          {submitting ? 'Saglabā...' : 'Saglabāt'}
        </button>
        {error && <span className="text-sm text-danger">{error}</span>}
      </div>
    </form>
  );
}
