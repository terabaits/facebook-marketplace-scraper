-- Note: the original spec used `provider = icu, locale = 'lv'` which fails on
-- this build because ICU does not recognize the bare `lv` tag. The
-- collprovider 'i' (icu) collations are pre-installed under BCP-47 names like
-- `lv-x-icu`; we alias it as `latvian` so the rest of the schema can reference
-- COLLATE "latvian" without hardcoding the BCP-47 form.
CREATE COLLATION IF NOT EXISTS latvian FROM "lv-x-icu";
