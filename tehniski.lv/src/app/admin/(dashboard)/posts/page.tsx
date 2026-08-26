import { db } from '@/lib/db';
import Link from 'next/link';
import { formatDateLv } from '@/lib/format';
import { PostStatusBadge } from '@/components/post-status-badge';

export default async function PostsList({
  searchParams
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const sp = await searchParams;
  const status = sp.status as any;
  const posts = await db.post.findMany({
    where: { deleted_at: null, ...(status ? { status } : {}) },
    orderBy: { updated_at: 'desc' },
    take: 100,
    include: { category: true, author: true }
  });
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Raksti</h1>
        <Link
          href="/admin/posts/new"
          className="bg-accent-primary text-bg-base font-bold px-4 py-2 rounded-md"
        >
          Jauns raksts
        </Link>
      </div>
      <div className="flex gap-2 mb-4 text-sm">
        <Link href="/admin/posts" className={!status ? 'font-bold underline' : 'hover:underline'}>
          Visi
        </Link>
        <Link
          href="/admin/posts?status=draft"
          className={status === 'draft' ? 'font-bold underline' : 'hover:underline'}
        >
          Melnraksti
        </Link>
        <Link
          href="/admin/posts?status=published"
          className={status === 'published' ? 'font-bold underline' : 'hover:underline'}
        >
          Publicētie
        </Link>
        <Link
          href="/admin/posts?status=scheduled"
          className={status === 'scheduled' ? 'font-bold underline' : 'hover:underline'}
        >
          Plānotie
        </Link>
        <Link
          href="/admin/posts?status=archived"
          className={status === 'archived' ? 'font-bold underline' : 'hover:underline'}
        >
          Arhivētie
        </Link>
      </div>
      <table className="w-full text-sm">
        <thead className="text-left text-text-secondary border-b border-border">
          <tr>
            <th className="py-2">Virsraksts</th>
            <th>Statuss</th>
            <th>Autors</th>
            <th>Atjaunināts</th>
          </tr>
        </thead>
        <tbody>
          {posts.map((p) => (
            <tr key={p.id} className="border-b border-border hover:bg-bg-subtle">
              <td className="py-2">
                <Link href={`/admin/posts/${p.id}`} className="hover:text-accent-primary">
                  {p.title}
                </Link>
              </td>
              <td>
                <PostStatusBadge status={p.status} />
              </td>
              <td>{p.author.name}</td>
              <td className="font-mono text-xs">{formatDateLv(p.updated_at)}</td>
            </tr>
          ))}
          {posts.length === 0 && (
            <tr>
              <td colSpan={4} className="py-6 text-center text-text-secondary">
                Nav neviena raksta
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
