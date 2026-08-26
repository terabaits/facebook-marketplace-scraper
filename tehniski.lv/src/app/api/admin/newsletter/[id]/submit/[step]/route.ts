import { NextRequest, NextResponse } from 'next/server';
import { Prisma } from '@prisma/client';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { parseStepResponse } from '@/lib/editorial/parser';
import { nextStatusFor } from '@/lib/editorial/state-machine';
import { slugify } from '@/lib/slug';
import { renderMarkdown } from '@/lib/markdown';
import type { StepName } from '@/lib/editorial/schemas';

export async function POST(req: NextRequest, ctx: { params: Promise<{ id: string; step: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id, step } = await ctx.params;
  if (!['pick-stories', 'pick-subject', 'write'].includes(step)) {
    return NextResponse.json({ error: 'Invalid step' }, { status: 400 });
  }

  const { response, selection_id } = await req.json();
  const result = parseStepResponse(step as StepName, response ?? '');
  if (!result.ok) return NextResponse.json({ error: result.error, partial: result.partialData }, { status: 400 });

  const run = await db.newsletterRun.findUnique({ where: { id } });
  if (!run) return NextResponse.json({ error: 'Not found' }, { status: 404 });

  // Persist step results
  if (step === 'pick-stories') {
    const data = result.data as {
      candidates: Array<{ story_id: string; title: string; source: string; reasoning: string; rank: number }>;
      intro?: string;
      shortlist?: string[];
      iteration_notes?: string;
    };
    await db.$transaction([
      // Clear existing selections for this run
      db.storySelection.deleteMany({ where: { run_id: id } }),
      // Insert new candidates
      ...data.candidates.map((c) => db.storySelection.create({
        data: {
          run_id: id,
          scraped_story_id: c.story_id,
          rank: c.rank,
          notes: c.reasoning,
          approved: false
        }
      })),
      // Update run with intro + shortlist
      db.newsletterRun.update({
        where: { id },
        data: {
          editor_feedback: data.intro ?? null, // intro saved as feedback for next step
          subject_alternatives: data.shortlist ? (data.shortlist as unknown as Prisma.InputJsonValue) : Prisma.JsonNull,
          status: nextStatusFor('pick-stories', run.status)
        }
      })
    ]);
  } else if (step === 'pick-subject') {
    const data = result.data as { main: string; alternatives: string[]; iteration_notes?: string };
    await db.newsletterRun.update({
      where: { id },
      data: {
        subject_main: data.main,
        subject_alternatives: data.alternatives as unknown as Prisma.InputJsonValue,
        selected_subject: data.main,
        status: nextStatusFor('pick-subject', run.status)
      }
    });
  } else if (step === 'write') {
    if (!selection_id) return NextResponse.json({ error: 'selection_id required for write step' }, { status: 400 });
    const data = result.data as { title_lv: string; excerpt_lv: string; body_md: string; iteration_notes?: string };
    // Find the selection with its scraped_story so we can pull the source URL
    const sel = await db.storySelection.findUnique({
      where: { id: selection_id },
      include: { scraped_story: { select: { url: true } } }
    });
    if (!sel) return NextResponse.json({ error: 'Selection not found' }, { status: 404 });

    // Ensure a draft author exists (single seeded author in this project)
    const author = await db.author.findFirst();
    if (!author) return NextResponse.json({ error: 'No author seeded; run db:seed' }, { status: 500 });

    // Create a Post row in 'draft' status, linked to the StorySelection
    const baseSlug = slugify(data.title_lv) || 'post';
    const post = await db.$transaction(async (tx) => {
      const p = await tx.post.create({
        data: {
          title: data.title_lv,
          slug: `${baseSlug}-${Date.now().toString(36).slice(-4)}`,
          excerpt: data.excerpt_lv,
          content_md: data.body_md,
          content_html: renderMarkdown(data.body_md),
          status: 'draft',
          source: 'newsletter',
          source_url: sel.scraped_story.url,
          newsletter_run_id: id,
          published_at: null,
          view_count: 0,
          language: 'lv',
          author_id: author.id
        }
      });
      await tx.storySelection.update({
        where: { id: selection_id },
        data: { approved: true, post_id: p.id }
      });
      return p;
    });
    // After write step, check if all approved stories are written → keep in 'writing' until bulk publish
    const remaining = await db.storySelection.count({ where: { run_id: id, approved: false } });
    if (remaining === 0) {
      // All approved — can move to publishing (but stay in 'writing' until publish action)
      // Actually keep in 'writing' until publish action
    }
    return NextResponse.json({ ok: true, post_id: post.id });
  }

  return NextResponse.json({ ok: true });
}
