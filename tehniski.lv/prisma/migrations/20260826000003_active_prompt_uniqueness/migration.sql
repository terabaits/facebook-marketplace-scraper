CREATE UNIQUE INDEX prompt_active_unique ON "PromptTemplate" (key)
  WHERE active = true;
