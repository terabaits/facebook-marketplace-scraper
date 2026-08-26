import { db } from '@/lib/db';
import { lv } from '@/lib/lv';
import { CommentTree } from './comment-tree';
import { CommentForm } from './comment-form';

export async function CommentSection({ postId, postSlug }: { postId: string; postSlug: string }) {
  const count = await db.comment.count({ where: { post_id: postId, status: 'approved' } });
  return (
    <section id="comments" className="border-t border-border pt-8 mt-8">
      <h2 className="text-xl font-bold mb-4">💬 {lv.plural.comments(count)}</h2>
      <CommentForm postId={postId} />
      <CommentTree postId={postId} />
    </section>
  );
}
