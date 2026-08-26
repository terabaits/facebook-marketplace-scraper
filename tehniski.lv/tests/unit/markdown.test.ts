import { describe, it, expect } from 'vitest';
import { renderMarkdown } from '@/lib/markdown';

describe('renderMarkdown', () => {
  it('renders headings', () => {
    expect(renderMarkdown('# Sveiki')).toContain('<h1');
    expect(renderMarkdown('# Sveiki')).toContain('Sveiki');
  });
  it('renders bold and italic', () => {
    expect(renderMarkdown('**strong**')).toContain('<strong>strong</strong>');
    expect(renderMarkdown('*em*')).toContain('<em>em</em>');
  });
  it('renders code blocks', () => {
    expect(renderMarkdown('```\nfoo\n```')).toContain('<pre');
  });
  it('sanitizes script tags', () => {
    expect(renderMarkdown('<script>alert(1)</script>')).not.toContain('<script>');
  });
  it('sanitizes inline event handlers', () => {
    expect(renderMarkdown('<a href="x" onclick="bad()">x</a>')).not.toContain('onclick');
  });
  it('preserves Latvian diacritics', () => {
    expect(renderMarkdown('Rīga')).toContain('Rīga');
  });
});
