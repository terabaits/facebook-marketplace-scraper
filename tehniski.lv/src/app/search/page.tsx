import { db } from '@/lib/db';
import { PostCard } from '@/components/post-card';
import { lv } from '@/lib/lv';

export const revalidate = 60;

export default async function SearchPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q: rawQ } = await searchParams;
  const q = (rawQ ?? '').trim();

  // Run the two reads in parallel — they're independent.
  const [posts, suggestions] = await Promise.all([
    q
      ? db.$queryRaw<Array<{ id: string; slug: string; title: string; excerpt: string; published_at: Date; cover_image_url: string | null }>>`
          SELECT id, slug, title, excerpt, published_at, cover_image_url
          FROM "Post"
          WHERE status = 'published' AND deleted_at IS NULL
            AND search_vector @@ plainto_tsquery('latvian', ${q})
          ORDER BY ts_rank(search_vector, plainto_tsquery('latvian', ${q})) DESC, published_at DESC
          LIMIT 30
        `
      : Promise.resolve([]),
    // Autocomplete suggestions: 10 most recent published posts. Browser-native
    // <datalist> just shows these as hints — the actual search runs on submit.
    db.post.findMany({
      where: { status: 'published', deleted_at: null },
      orderBy: { published_at: 'desc' },
      take: 10,
      select: { id: true, title: true }
    })
  ]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">{lv.search.title}</h1>
      <form method="get" className="mb-2" role="search">
        <label htmlFor="q" className="sr-only">{lv.search.placeholder}</label>
        <input
          id="q"
          name="q"
          defaultValue={q}
          list="popular-titles"
          autoComplete="off"
          placeholder={lv.search.placeholder}
          aria-label={lv.search.placeholder}
          className="w-full bg-bg-elevated border border-border rounded-md px-4 py-2"
        />
        <datalist id="popular-titles">
          {suggestions.map(s => (
            <option key={s.id} value={s.title} />
          ))}
        </datalist>
      </form>
      <p className="text-xs text-text-secondary mb-6" aria-hidden={suggestions.length === 0}>
        {suggestions.length > 0 ? `${lv.search.suggestionsHint}: ${suggestions.length}` : ''}
      </p>
      {q && <p className="text-sm text-text-secondary mb-4">{lv.search.resultsFor(q, posts.length)}</p>}
      <div className="grid grid-cols-12 gap-6">
        {posts.map(p => <PostCard key={p.id} post={{ ...p, _count: { comments: 0 } } as any} size="small" />)}
      </div>
    </div>
  );
}
