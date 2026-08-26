import { db } from '@/lib/db';
import { pickCreative } from './ads';
import { cache } from 'react';

export const getActiveCreatives = cache(async (slotKey: string) => {
  const slot = await db.adSlot.findUnique({ where: { key: slotKey } });
  if (!slot || !slot.active) return null;
  const now = new Date();
  const creatives = await db.adCreative.findMany({
    where: {
      slot_id: slot.id, active: true,
      OR: [{ starts_at: null }, { starts_at: { lte: now } }],
      AND: [{ OR: [{ ends_at: null }, { ends_at: { gte: now } }] }]
    }
  });
  return { slot, creative: pickCreative(creatives) };
});
