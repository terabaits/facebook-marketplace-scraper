import { db } from '@/lib/db';
import { formatRelativeLv } from '@/lib/format';
import { lv } from '@/lib/lv';
import { CommentForm } from './comment-form';

export async function CommentTree({ postId }: { postId: string }) {
  const comments = await db.comment.findMany({
    where: { post_id: postId, parent_id: null, status: 'approved' },
    orderBy: { created_at: 'asc' },
    take: 50,
    include: { replies: { where: { status: 'approved' }, orderBy: { created_at: 'asc' }, take: 5 } }
  });
  if (comments.length === 0) return <p className="text-text-secondary text-sm">Nav komentāru. Esiet pirmais!</p>;
  return (
    <div className="space-y-4">
      {comments.map(c => <CommentNode key={c.id} comment={c} postId={postId} />)}
    </div>
  );
}

function CommentNode({ comment, postId, depth = 0 }: { comment: any; postId: string; depth?: number }) {
  const visualIndent = Math.min(depth, 5);
  return (
    <div style={{ marginLeft: `${visualIndent * 24}px` }} className="border-l border-border pl-4">
      <div className={`flex items-center gap-2 text-sm ${comment.is_author ? 'text-accent-secondary font-bold' : ''}`}>
        <span>{comment.author_name}</span>
        {comment.is_author && <span className="text-xs bg-accent-secondary text-bg-base px-1.5 rounded">✦ {lv.comment.author}</span>}
        <span className="font-mono text-xs text-text-secondary">{formatRelativeLv(comment.created_at)}</span>
      </div>
      <p className="text-sm mt-1 whitespace-pre-wrap">{comment.body}</p>
      <details className="mt-2">
        <summary className="text-xs text-text-secondary cursor-pointer">Atbildēt</summary>
        <div className="mt-2"><CommentForm postId={postId} parentId={comment.id} /></div>
      </details>
      {comment.replies?.map((r: any) => <CommentNode key={r.id} comment={r} postId={postId} depth={depth + 1} />)}
    </div>
  );
}
