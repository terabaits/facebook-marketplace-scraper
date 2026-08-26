import { db } from '@/lib/db';
import { PostForm } from '../../_components/post-form';

export default async function NewPostPage() {
  const categories = await db.category.findMany({ orderBy: { name: 'asc' } });
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Jauns raksts</h1>
      <PostForm categories={categories} />
    </div>
  );
}
