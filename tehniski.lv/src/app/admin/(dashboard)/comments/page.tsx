import { db } from '@/lib/db';
import Link from 'next/link';
import { formatRelativeLv } from '@/lib/format';
import { ModerationActions } from '../_components/moderation-actions';

export default async function CommentsPage({ searchParams }: { searchParams: Promise<{ status?: string }> }) {
  const sp = await searchParams;
  const status = (sp.status ?? 'pending') as any;
  const comments = await db.comment.findMany({
    where: { status, parent_id: null },
    orderBy: { created_at: 'desc' },
    take: 100,
    include: { post: { select: { slug: true, title: true } } }
  });
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Komentāri</h1>
      <div className="flex gap-2 mb-4 text-sm">
        <Link href="/admin/comments?status=pending" className={status === 'pending' ? 'font-bold' : ''}>Gaida</Link>
        <Link href="/admin/comments?status=approved" className={status === 'approved' ? 'font-bold' : ''}>Apstiprināti</Link>
        <Link href="/admin/comments?status=spam" className={status === 'spam' ? 'font-bold' : ''}>Spams</Link>
      </div>
      <div className="space-y-3">
        {comments.map(c => (
          <div key={c.id} className="bg-bg-elevated border border-border rounded-md p-4">
            <div className="flex justify-between mb-2">
              <div>
                <span className="font-bold">{c.author_name}</span>
                <span className="ml-2 font-mono text-xs text-text-secondary">{formatRelativeLv(c.created_at)}</span>
                {c.is_author && <span className="ml-2 text-xs text-accent-secondary">✦ Autors</span>}
              </div>
              <Link href={`/post/${c.post.slug}#comment-${c.id}`} target="_blank" className="text-xs text-text-secondary hover:text-accent-primary">{c.post.title} ↗</Link>
            </div>
            <p className="text-sm whitespace-pre-wrap mb-3">{c.body}</p>
            <ModerationActions commentId={c.id} />
          </div>
        ))}
      </div>
    </div>
  );
}
