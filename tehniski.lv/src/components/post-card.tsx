import Link from 'next/link';
import { formatDateLv } from '@/lib/format';
import { lv } from '@/lib/lv';
import type { Post } from '@prisma/client';

type PostWithCount = Post & { _count: { comments: number } };

export function PostCard({ post, size }: { post: PostWithCount; size: 'big' | 'medium' | 'small' }) {
  const sizes = {
    big: 'col-span-6',
    medium: 'col-span-3',
    small: 'col-span-4'
  } as const;
  const commentCount = post._count?.comments ?? 0;
  return (
    <Link href={`/post/${post.slug}`} className={`block ${sizes[size]} group`}>
      {post.cover_image_url && (
        <div className="aspect-video bg-bg-subtle overflow-hidden rounded-md mb-3">
          <img src={post.cover_image_url} alt={post.cover_image_alt ?? post.title} className="w-full h-full object-cover" />
        </div>
      )}
      <h3 className={`font-bold group-hover:text-accent-primary ${size === 'big' ? 'text-2xl' : 'text-base'}`}>
        {post.title}
      </h3>
      <div className="mt-2 font-mono text-xs text-text-secondary">
        💬 {lv.plural.comments(commentCount)} · {formatDateLv(post.published_at ?? new Date())}
      </div>
    </Link>
  );
}
