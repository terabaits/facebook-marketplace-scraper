import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { JSDOM } from 'jsdom';

const window = new JSDOM('').window;
const purify = DOMPurify(window as any);

marked.setOptions({ gfm: true, breaks: false });

export function renderMarkdown(md: string): string {
  const html = marked.parse(md, { async: false }) as string;
  return purify.sanitize(html, {
    ALLOWED_TAGS: ['h1','h2','h3','h4','h5','h6','p','a','ul','ol','li','strong','em','code','pre','blockquote','img','br','hr','table','thead','tbody','tr','th','td'],
    ALLOWED_ATTR: ['href','src','alt','title']
  });
}
