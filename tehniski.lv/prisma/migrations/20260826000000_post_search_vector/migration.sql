-- Generated tsvector column for Latvian FTS. NOT in Prisma schema.
--
-- Note: the PostgreSQL build on this host does not ship a Latvian text search
-- configuration (no `latvian_stem` dictionary). We register a `latvian` text
-- search config that copies the `simple` dictionary so the to_tsvector('latvian', ...)
-- calls below resolve. This means stemming/stopwords are language-agnostic.
-- To get proper Latvian stemming, install postgresql-contrib with latvian language
-- support (or rebuild PostgreSQL with --with-extra-languages) and drop this
-- DO block; the native `latvian` config will then be used by the generated column.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'latvian') THEN
    CREATE TEXT SEARCH CONFIGURATION latvian ( COPY = simple );
  END IF;
END
$$;

ALTER TABLE "Post"
  ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('latvian', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('latvian', coalesce(excerpt, '')), 'B') ||
    setweight(to_tsvector('latvian', coalesce(content_md, '')), 'C')
  ) STORED;

CREATE INDEX post_search_vector_idx ON "Post" USING GIN (search_vector);
