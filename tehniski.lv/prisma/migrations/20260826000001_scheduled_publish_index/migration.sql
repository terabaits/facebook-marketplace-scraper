CREATE INDEX post_scheduled_publish_idx ON "Post" (publish_at)
  WHERE status = 'scheduled';
