// Dump the article body context
const url = 'http://localhost:5002/post/openai-lai%C5%BE-klaj%C4%81-jaunu-gpt-modeli-0';
(async () => {
  const r = await fetch(url);
  const html = await r.text();
  // Find the article tag
  const articleStart = html.indexOf('<article');
  const articleEnd = html.indexOf('</article>');
  console.log('article starts:', articleStart, 'ends:', articleEnd);
  if (articleStart >= 0) {
    const body = html.slice(articleStart, articleEnd + '</article>'.length);
    // Strip tags from key chunks
    const textOnly = body.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').slice(0, 2000);
    console.log('--- article text (first 2k chars) ---');
    console.log(textOnly);
    console.log('--- ad slots in body ---');
    const adMatches = body.match(/Ad slot: ?[a-zA-Z_0-9]*/g) || [];
    adMatches.forEach(m => console.log(' ', JSON.stringify(m)));
  }
})();
