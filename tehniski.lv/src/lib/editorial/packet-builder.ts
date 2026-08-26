import { db } from '@/lib/db';
import type { StepName } from './schemas';

const MAX_BODY_EXCERPT_BYTES = 10 * 1024;  // 10KB cap per story

/**
 * Wraps scraped content in <source> delimiters and tells Mavis to treat it as data, not instructions.
 * This is defense in depth — Mavis is trusted, but the convention is kept as a habit.
 */
function wrapSource(content: string, sourceName: string, url: string): string {
  return `<source name="${escapeAttr(sourceName)}" url="${escapeAttr(url)}">\n${content}\n</source>`;
}

function escapeAttr(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}

function truncateMarkdown(s: string, maxBytes: number): string {
  if (Buffer.byteLength(s, 'utf8') <= maxBytes) return s;
  // Cut by characters to keep valid UTF-8
  let out = s;
  while (Buffer.byteLength(out, 'utf8') > maxBytes && out.length > 0) out = out.slice(0, -1);
  return out + '\n\n[… saturs saīsināts līdz 10 KB …]';
}

export type PacketContext = {
  runId: string;
  feedback?: string;          // editor_feedback from previous iteration
  iterationNotes?: string;   // what changed vs prior iteration
};

/**
 * Build the task packet for the pick-stories step.
 * Includes: system prompt, candidate scraped stories (title, source, summary, body excerpt),
 * the strict JSON output schema, and the <source> delimiters.
 */
export async function buildPickStoriesPacket(ctx: PacketContext): Promise<string> {
  const prompt = await db.promptTemplate.findFirst({
    where: { key: 'pick-stories', active: true }
  });
  if (!prompt) throw new Error('No active prompt template for key=pick-stories');

  // Candidate pool: 30 most recent 'new' scraped stories
  const candidates = await db.scrapedStory.findMany({
    where: { status: 'new' },
    orderBy: { scraped_at: 'desc' },
    take: 30,
    include: { source: { select: { name: true } } }
  });

  const run = await db.newsletterRun.findUnique({ where: { id: ctx.runId } });
  if (!run) throw new Error(`NewsletterRun not found: ${ctx.runId}`);

  // Build the per-story block
  const storyBlocks = candidates.map((s, i) => {
    const body = truncateMarkdown(s.markdown ?? '', MAX_BODY_EXCERPT_BYTES);
    const wrapped = wrapSource(
      `Title: ${s.title}\nSource: ${s.source.name}\nURL: ${s.url}\nPublished: ${s.published_at_src?.toISOString() ?? 'unknown'}\nSummary: ${s.summary ?? '(none)'}\n\n${body}`,
      s.source.name,
      s.url
    );
    return `### Kandidāts ${i + 1} (id: ${s.id})\n${wrapped}`;
  }).join('\n\n---\n\n');

  const feedbackBlock = ctx.feedback
    ? `\n\n## Iepriekšējās iterācijas atsauksmes\n\n${wrapSource(ctx.feedback, 'editor', 'inline')}\n`
    : '';
  const iterationBlock = ctx.iterationNotes
    ? `\n\n## Kas mainījies\n\n${ctx.iterationNotes}\n`
    : '';

  // The packet ends with the strict JSON output schema (Mavis's contract)
  return `${prompt.system_prompt}

## Uzdevums

Mērķa datums: ${run.target_date.toISOString().slice(0, 10)}

Izvēlies 3-7 labākos stāstus no kandidātu saraksta. Katram norādi:
- story_id (tieši tāds pats kā kandidāta ID)
- title (oriģinālais nosaukums)
- source (avota nosaukums)
- reasoning (1-2 teikumi, kāpēc šo stāstu izvēlējies)
- rank (1 = labākais)

Papildus:
- intro: ~1 rindkopas Latvian ievadrunā dienas tēmai
- shortlist: 3-5 citu labu kandidātu nosaukumi, kurus nepublicēsim
- iteration_notes: ko tu mainīji, salīdzinot ar iepriekšējo iterāciju (ja ir)

## Kandidātu saraksts

${storyBlocks}${feedbackBlock}${iterationBlock}

## Atbildes formāts

Atgriez TIKAI JSON objektu (bez paskaidrojuma pirms vai pēc):

${prompt.user_prompt}

Piemērs:
\`\`\`json
{
  "candidates": [
    { "story_id": "ckxxxxxxxxxxxx", "title": "...", "source": "...", "reasoning": "...", "rank": 1 }
  ],
  "intro": "Šodien tehnoloģiju pasaulē...",
  "shortlist": ["...", "..."],
  "iteration_notes": "Salīdzinot ar iepriekšējo iterāciju, šoreiz..."
}
\`\`\`
`;
}

/**
 * Build the task packet for the pick-subject step.
 * Input: the approved story selections from the pick-stories step.
 */
export async function buildPickSubjectPacket(ctx: PacketContext): Promise<string> {
  const prompt = await db.promptTemplate.findFirst({
    where: { key: 'pick-subject', active: true }
  });
  if (!prompt) throw new Error('No active prompt template for key=pick-subject');

  const run = await db.newsletterRun.findUnique({
    where: { id: ctx.runId },
    include: {
      selections: {
        where: { approved: true },
        orderBy: { rank: 'asc' },
        include: { scraped_story: { include: { source: { select: { name: true } } } } }
      }
    }
  });
  if (!run) throw new Error(`NewsletterRun not found: ${ctx.runId}`);

  const storyBlocks = run.selections.map((sel, i) => {
    const s = sel.scraped_story;
    return `### Stāsts ${i + 1}: ${s.title}\nAvots: ${s.source.name}\nPārskats: ${s.summary ?? '(none)'}\nRank: ${sel.rank}\n`;
  }).join('\n');

  const feedbackBlock = ctx.feedback
    ? `\n## Iepriekšējās iterācijas atsauksmes\n\n${wrapSource(ctx.feedback, 'editor', 'inline')}\n`
    : '';

  return `${prompt.system_prompt}

## Uzdevums

Izveido dienasnewsletter temata nosaukumu (subject) un 3-5 alternatīvas.

Mērķa datums: ${run.target_date.toISOString().slice(0, 10)}

## Apstiprinātie stāsti

${storyBlocks}${feedbackBlock}

## Atbildes formāts

Atgriez TIKAI JSON objektu:

${prompt.user_prompt}

Piemērs:
\`\`\`json
{
  "main": "Šodienas galvenais temats",
  "alternatives": ["Alt 1", "Alt 2", "Alt 3", "Alt 4"]
}
\`\`\`
`;
}

/**
 * Build the task packet for the write step. One packet per approved story.
 * Input: a single approved StorySelection.
 */
export async function buildWritePacket(ctx: PacketContext, selectionId: string): Promise<string> {
  const prompt = await db.promptTemplate.findFirst({
    where: { key: 'write', active: true }
  });
  if (!prompt) throw new Error('No active prompt template for key=write');

  const selection = await db.storySelection.findUnique({
    where: { id: selectionId },
    include: { scraped_story: { include: { source: { select: { name: true } } } } }
  });
  if (!selection) throw new Error(`StorySelection not found: ${selectionId}`);

  const s = selection.scraped_story;
  const body = truncateMarkdown(s.markdown ?? '', MAX_BODY_EXCERPT_BYTES);
  const wrapped = wrapSource(
    `Title: ${s.title}\nSource: ${s.source.name}\nURL: ${s.url}\n\n${body}`,
    s.source.name,
    s.url
  );

  const feedbackBlock = ctx.feedback
    ? `\n## Iepriekšējās iterācijas atsauksmes\n\n${wrapSource(ctx.feedback, 'editor', 'inline')}\n`
    : '';

  return `${prompt.system_prompt}

## Uzdevums

Pārtulko un pārstrādā šo stāstu latviski. Saglabā faktus, bet pielāgo stilu vietējam tech-ziņu portālam.

${wrapped}${feedbackBlock}

## Atbildes formāts

Atgriez TIKAI JSON objektu:

${prompt.user_prompt}

Piemērs:
\`\`\`json
{
  "title_lv": "Latvisks nosaukums",
  "excerpt_lv": "1-2 teikumu kopsavilkums",
  "body_md": "## Virsraksts\n\nRaksta pirmā rindkopa...\n\n## Apakšvirsraksts\n\nVairāk satura..."
}
\`\`\`
`;
}

export async function buildPacket(step: StepName, ctx: PacketContext, selectionId?: string): Promise<string> {
  if (step === 'pick-stories') return buildPickStoriesPacket(ctx);
  if (step === 'pick-subject') return buildPickSubjectPacket(ctx);
  if (step === 'write') return buildWritePacket(ctx, selectionId!);
  throw new Error(`Unknown step: ${step}`);
}
