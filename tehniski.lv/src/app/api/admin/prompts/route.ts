import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';

const schema = z.object({
  key: z.string().min(1),
  name: z.string().min(1),
  description: z.string().optional(),
  system_prompt: z.string().min(1),
  user_prompt: z.string().min(1),
  model: z.string().default('unset'),
  temperature: z.number().min(0).max(2).default(0.7),
  set_active: z.boolean().default(false)
});

export async function POST(req: NextRequest) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const data = schema.parse(await req.json());

  // Find the latest version for this key
  const latest = await db.promptTemplate.findFirst({
    where: { key: data.key },
    orderBy: { version: 'desc' }
  });
  const nextVersion = (latest?.version ?? 0) + 1;

  // If set_active, deactivate siblings in a transaction
  const prompt = await db.$transaction(async (tx) => {
    if (data.set_active) {
      await tx.promptTemplate.updateMany({
        where: { key: data.key, active: true },
        data: { active: false }
      });
    }
    return tx.promptTemplate.create({
      data: {
        key: data.key,
        version: nextVersion,
        name: data.name,
        description: data.description,
        system_prompt: data.system_prompt,
        user_prompt: data.user_prompt,
        model: data.model,
        temperature: data.temperature,
        active: data.set_active,
        created_by: session.user?.email ?? 'unknown'
      }
    });
  });
  return NextResponse.json(prompt);
}
