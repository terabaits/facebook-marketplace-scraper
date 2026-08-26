// Clean verification: focus on key signal
const cases = [
  {
    name: 'Post page (OpenAI, has diacritics)',
    url: 'http://localhost:5002/post/openai-lai%C5%BE-klaj%C4%81-jaunu-gpt-modeli-0',
    expectStatus: 200,
    mustContain: [
      'OpenAI laiž klajā jaunu GPT modeli',
      'application/ld+json',
      '"@type":"Article"',
      '"headline":"OpenAI laiž klajā jaunu GPT modeli"',
      '"publisher":{"@type":"Organization","name":"tehniski.lv"}',
      '"name":"Redaktors"',
      'Vairāk no tehniski.lv',
      'Komentāri',
      'Komentāru sistēma tiks pievienota drīzumā',
      'post_top',
      'post_right_rail',
      'AI',
      '26.08.2026.',
      '0 komentāri'
    ]
  },
  {
    name: 'Post page (no diacritics)',
    url: 'http://localhost:5002/post/linux-610-jaunumi-3',
    expectStatus: 200,
    mustContain: ['Linux 6.10 jaunumi', '"@type":"Article"', 'Vairāk no tehniski.lv']
  },
  {
    name: 'Category /ai',
    url: 'http://localhost:5002/category/ai',
    expectStatus: 200,
    mustContain: ['>AI<', 'OpenAI laiž klajā jaunu GPT modeli', 'Kā darbojas LLM']
  },
  {
    name: 'Search page (OpenAI)',
    url: 'http://localhost:5002/search?q=OpenAI',
    expectStatus: 200,
    mustContain: ['>Meklēšana<', 'rezultāti vaicājumam', 'OpenAI laiž klajā jaunu GPT modeli']
  },
  {
    name: 'Search API (OpenAI)',
    url: 'http://localhost:5002/api/search?q=OpenAI',
    expectStatus: 200,
    mustContain: ['"results":[', '"title":"OpenAI laiž klajā jaunu GPT modeli"'],
    isJson: true
  },
  {
    name: 'RSS feed',
    url: 'http://localhost:5002/rss.xml',
    expectStatus: 200,
    mustContain: ['<?xml', '<rss version="2.0">', '<title>tehniski.lv</title>', '<language>lv</language>', '<item>', 'openai-laiž-klajā-jaunu-gpt-modeli-0'],
    mustMatchGt: { '<item>': 9 } // at least 10 posts
  },
  {
    name: 'Sitemap',
    url: 'http://localhost:5002/sitemap.xml',
    expectStatus: 200,
    mustContain: ['<?xml', '<urlset', 'http://localhost:5002</loc>', '/category/ai', '/category/security', '/category/software', '/category/hardware', '/post/openai-laiž-klajā-jaunu-gpt-modeli-0']
  },
  {
    name: 'Robots',
    url: 'http://localhost:5002/robots.txt',
    expectStatus: 200,
    mustContain: ['User-agent: *', 'Allow: /', 'Sitemap: http://localhost:5002/sitemap.xml']
  },
  {
    name: 'Search API empty result',
    url: 'http://localhost:5002/api/search?q=zzzzzzzznonexistent',
    expectStatus: 200,
    mustContain: ['"results":[]'],
    isJson: true
  },
  {
    name: 'Search API invalid (empty q)',
    url: 'http://localhost:5002/api/search?q=',
    expectStatus: 400,
    isJson: true
  },
  {
    name: 'Search query was logged to DB',
    url: null,
    postCheck: async () => {
      const { PrismaClient } = require('@prisma/client');
      const db = new PrismaClient();
      const recent = await db.searchQuery.findMany({ orderBy: { occurred_at: 'desc' }, take: 5 });
      await db.$disconnect();
      return recent.length > 0 && recent.some(r => r.query && r.ip_hash);
    }
  },
  {
    name: 'Not found: bad post slug',
    url: 'http://localhost:5002/post/does-not-exist-zzz',
    expectStatus: 404
  },
  {
    name: 'Not found: bad category',
    url: 'http://localhost:5002/category/does-not-exist',
    expectStatus: 404
  }
];

(async () => {
  let pass = 0, fail = 0;
  for (const c of cases) {
    if (c.postCheck) {
      const ok = await c.postCheck();
      console.log(`${ok ? '✓' : '✗'}  ${c.name}`);
      if (ok) pass++; else fail++;
      continue;
    }
    try {
      const r = await fetch(c.url);
      const text = await r.text();
      const ok = r.status === c.expectStatus &&
        (!c.mustContain || c.mustContain.every(s => text.includes(s))) &&
        (!c.mustMatchGt || Object.entries(c.mustMatchGt).every(([s, n]) => (text.match(new RegExp(s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length > n));
      console.log(`${ok ? '✓' : '✗'}  [${r.status}] ${c.name}`);
      if (!ok) {
        if (r.status !== c.expectStatus) console.log(`      expected status ${c.expectStatus}, got ${r.status}`);
        if (c.mustContain) {
          for (const s of c.mustContain) if (!text.includes(s)) console.log(`      MISSING: ${s.slice(0, 80)}`);
        }
        if (c.mustMatchGt) {
          for (const [s, n] of Object.entries(c.mustMatchGt)) {
            const count = (text.match(new RegExp(s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
            if (count <= n) console.log(`      count[${s}] = ${count}, expected > ${n}`);
          }
        }
        fail++;
      } else {
        pass++;
      }
    } catch (e) {
      console.log(`✗  ERR ${c.name}: ${e.message}`);
      fail++;
    }
  }
  console.log(`\n${pass} pass, ${fail} fail`);
  process.exit(fail > 0 ? 1 : 0);
})();
