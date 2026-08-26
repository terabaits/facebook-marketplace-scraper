// Verify all routes — uses native node fetch (decodes URLs properly)
const cases = [
  // Post page — slug with Latvian diacritics
  'http://localhost:5002/post/openai-lai%C5%BE-klaj%C4%81-jaunu-gpt-modeli-0',
  // Same page, no diacritics
  'http://localhost:5002/post/linux-610-jaunumi-3',
  // Category
  'http://localhost:5002/category/ai',
  'http://localhost:5002/category/security',
  'http://localhost:5002/category/does-not-exist',
  // Search page
  'http://localhost:5002/search',
  'http://localhost:5002/search?q=OpenAI',
  'http://localhost:5002/search?q=Apple',
  // Search API
  'http://localhost:5002/api/search?q=OpenAI',
  'http://localhost:5002/api/search?q=Apple&limit=5',
  'http://localhost:5002/api/search?q=nonexistentterm',
  // RSS, sitemap, robots
  'http://localhost:5002/rss.xml',
  'http://localhost:5002/sitemap.xml',
  'http://localhost:5002/robots.txt'
];

(async () => {
  for (const url of cases) {
    try {
      const r = await fetch(url, { redirect: 'manual' });
      const text = await r.text();
      const snippet = text.length > 200 ? text.slice(0, 200).replace(/\s+/g, ' ') + `…(${text.length}B)` : text.replace(/\s+/g, ' ');
      console.log(`[${r.status}] ${url}`);
      console.log(`      ${snippet}`);
    } catch (e) {
      console.log(`[ERR] ${url} — ${e.message}`);
    }
  }
})();
