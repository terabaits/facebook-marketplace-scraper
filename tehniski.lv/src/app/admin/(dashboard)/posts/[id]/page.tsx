import { db } from '@/lib/db';
import { notFound } from 'next/navigation';
import { PostForm } from '../../_components/post-form';
import { PublishActions } from '../../_components/publish-actions';

export default async function EditPostPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const post = await db.post.findUnique({ where: { id, deleted_at: null } });
  if (!post) notFound();
  const categories = await db.category.findMany({ orderBy: { name: 'asc' } });
  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Rediģēt rakstu</h1>
      <p className="text-text-secondary text-sm mb-4 font-mono">slug: {post.slug}</p>
      <PublishActions post={post} />
      <PostForm categories={categories} post={post} />
    </div>
  );
}
