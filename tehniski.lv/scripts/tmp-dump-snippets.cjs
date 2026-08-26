// Dump interesting snippets from the post page
const url = 'http://localhost:5002/post/openai-lai%C5%BE-klaj%C4%81-jaunu-gpt-modeli-0';
(async () => {
  const r = await fetch(url);
  const html = await r.text();

  // Find ad-slot instances
  const adMatches = html.match(/Ad slot:[^<"]{0,50}/g) || [];
  console.log('--- Ad slot instances ---');
  adMatches.forEach(m => console.log(' ', m));

  // Find category line
  console.log('\n--- category breadcrumb context ---');
  const idx = html.indexOf('Vispārīgi');
  if (idx >= 0) console.log(html.slice(Math.max(0, idx-100), idx+200));
  const idxAI = html.indexOf('AI');
  console.log('AI index:', idxAI);
  if (idxAI >= 0) console.log('  context:', html.slice(Math.max(0, idxAI-200), idxAI+50).replace(/\s+/g, ' '));

  // Count all /post/ hrefs
  const allHrefs = (html.match(/href="\/post\/[^"]*"/g) || []);
  console.log('\n--- All /post/ hrefs ---');
  allHrefs.forEach(h => console.log(' ', h));

  // Check <title>
  const titleMatch = html.match(/<title>[^<]*<\/title>/);
  console.log('\n--- <title> ---');
  console.log(' ', titleMatch ? titleMatch[0] : 'NOT FOUND');
})();
