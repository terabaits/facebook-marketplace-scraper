-- CreateEnum
CREATE TYPE "PostStatus" AS ENUM ('draft', 'scheduled', 'published', 'archived');

-- CreateEnum
CREATE TYPE "SourceType" AS ENUM ('manual', 'newsletter');

-- CreateEnum
CREATE TYPE "FeaturedTier" AS ENUM ('big', 'medium');

-- CreateEnum
CREATE TYPE "CommentStatus" AS ENUM ('pending', 'approved', 'spam', 'deleted');

-- CreateEnum
CREATE TYPE "CreativeKind" AS ENUM ('image', 'embed');

-- CreateEnum
CREATE TYPE "AdEventKind" AS ENUM ('impression', 'click');

-- CreateEnum
CREATE TYPE "ScrapedStatus" AS ENUM ('new', 'used', 'ignored', 'failed');

-- CreateEnum
CREATE TYPE "RunStatus" AS ENUM ('in_progress', 'awaiting_editor', 'awaiting_subject', 'writing', 'published', 'failed');

-- CreateTable
CREATE TABLE "Author" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "bio" TEXT,
    "avatar_url" TEXT,
    "is_admin" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Author_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Category" (
    "id" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "name" TEXT NOT NULL,

    CONSTRAINT "Category_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Post" (
    "id" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "excerpt" TEXT NOT NULL,
    "content_md" TEXT NOT NULL,
    "content_html" TEXT NOT NULL,
    "cover_image_url" TEXT,
    "cover_image_alt" TEXT,
    "status" "PostStatus" NOT NULL,
    "publish_at" TIMESTAMP(3),
    "published_at" TIMESTAMP(3),
    "language" TEXT NOT NULL DEFAULT 'lv',
    "source" "SourceType" NOT NULL DEFAULT 'manual',
    "source_scraped_id" TEXT,
    "source_url" TEXT,
    "newsletter_run_id" TEXT,
    "author_id" TEXT NOT NULL,
    "category_id" TEXT,
    "featured_tier" "FeaturedTier",
    "featured_at" TIMESTAMP(3),
    "featured_order" INTEGER,
    "view_count" INTEGER NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,
    "deleted_at" TIMESTAMP(3),

    CONSTRAINT "Post_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Comment" (
    "id" TEXT NOT NULL,
    "post_id" TEXT NOT NULL,
    "parent_id" TEXT,
    "depth" INTEGER NOT NULL DEFAULT 0,
    "reply_count" INTEGER NOT NULL DEFAULT 0,
    "last_reply_at" TIMESTAMP(3),
    "author_id" TEXT,
    "author_name" TEXT NOT NULL,
    "author_email_hash" TEXT NOT NULL,
    "body" TEXT NOT NULL,
    "status" "CommentStatus" NOT NULL DEFAULT 'pending',
    "is_author" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Comment_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PostView" (
    "id" TEXT NOT NULL,
    "post_id" TEXT NOT NULL,
    "occurred_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "ip_hash" TEXT NOT NULL,
    "referer" TEXT,
    "user_agent" TEXT,
    "country" TEXT,

    CONSTRAINT "PostView_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "SearchQuery" (
    "id" TEXT NOT NULL,
    "query" TEXT NOT NULL,
    "result_count" INTEGER NOT NULL,
    "occurred_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "ip_hash" TEXT,

    CONSTRAINT "SearchQuery_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "AdSlot" (
    "id" TEXT NOT NULL,
    "key" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "width" INTEGER NOT NULL,
    "height" INTEGER NOT NULL,
    "active" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "AdSlot_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "AdCreative" (
    "id" TEXT NOT NULL,
    "slot_id" TEXT NOT NULL,
    "kind" "CreativeKind" NOT NULL,
    "image_url" TEXT,
    "target_url" TEXT,
    "alt_text" TEXT,
    "embed_html" TEXT,
    "starts_at" TIMESTAMP(3),
    "ends_at" TIMESTAMP(3),
    "weight" INTEGER NOT NULL DEFAULT 1,
    "active" BOOLEAN NOT NULL DEFAULT true,
    "impressions" INTEGER NOT NULL DEFAULT 0,
    "clicks" INTEGER NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "AdCreative_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "AdEvent" (
    "id" TEXT NOT NULL,
    "creative_id" TEXT NOT NULL,
    "kind" "AdEventKind" NOT NULL,
    "occurred_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "ip_hash" TEXT,
    "user_agent" TEXT,
    "post_id" TEXT,

    CONSTRAINT "AdEvent_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "RssSource" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "feed_url" TEXT NOT NULL,
    "site_url" TEXT NOT NULL,
    "parser_config" JSONB NOT NULL DEFAULT '{}',
    "active" BOOLEAN NOT NULL DEFAULT true,
    "last_fetched_at" TIMESTAMP(3),
    "last_error" TEXT,
    "scrape_count" INTEGER NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "RssSource_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ScrapedStory" (
    "id" TEXT NOT NULL,
    "source_id" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "url_hash" TEXT NOT NULL,
    "content_hash" TEXT,
    "title" TEXT NOT NULL,
    "author" TEXT,
    "published_at_src" TIMESTAMP(3),
    "scraped_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "language" TEXT NOT NULL DEFAULT 'en',
    "markdown" TEXT NOT NULL,
    "summary" TEXT,
    "word_count" INTEGER,
    "status" "ScrapedStatus" NOT NULL DEFAULT 'new',

    CONSTRAINT "ScrapedStory_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "NewsletterRun" (
    "id" TEXT NOT NULL,
    "target_date" TIMESTAMP(3) NOT NULL,
    "previous_run_id" TEXT,
    "started_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completed_at" TIMESTAMP(3),
    "status" "RunStatus" NOT NULL DEFAULT 'in_progress',
    "editor_feedback" TEXT,
    "editor_iterations" INTEGER NOT NULL DEFAULT 0,
    "subject_main" TEXT,
    "subject_alternatives" JSONB,
    "selected_subject" TEXT,
    "prompt_set" TEXT NOT NULL DEFAULT 'default',
    "llm_model" TEXT,
    "tokens_used" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "NewsletterRun_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "StorySelection" (
    "id" TEXT NOT NULL,
    "run_id" TEXT NOT NULL,
    "scraped_story_id" TEXT NOT NULL,
    "rank" INTEGER NOT NULL,
    "approved" BOOLEAN NOT NULL DEFAULT false,
    "notes" TEXT,
    "post_id" TEXT,

    CONSTRAINT "StorySelection_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PromptTemplate" (
    "id" TEXT NOT NULL,
    "key" TEXT NOT NULL,
    "version" INTEGER NOT NULL DEFAULT 1,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "system_prompt" TEXT NOT NULL,
    "user_prompt" TEXT NOT NULL,
    "model" TEXT NOT NULL DEFAULT 'unset',
    "temperature" DOUBLE PRECISION NOT NULL DEFAULT 0.7,
    "active" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "created_by" TEXT,

    CONSTRAINT "PromptTemplate_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "WorkerHeartbeat" (
    "id" TEXT NOT NULL DEFAULT 'singleton',
    "last_seen" TIMESTAMP(3) NOT NULL,
    "version" TEXT,
    "started_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "WorkerHeartbeat_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Setting" (
    "id" TEXT NOT NULL,
    "key" TEXT NOT NULL,
    "value" TEXT NOT NULL,

    CONSTRAINT "Setting_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Author_email_key" ON "Author"("email");

-- CreateIndex
CREATE UNIQUE INDEX "Category_slug_key" ON "Category"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "Post_slug_key" ON "Post"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "Post_source_scraped_id_key" ON "Post"("source_scraped_id");

-- CreateIndex
CREATE INDEX "Post_status_published_at_idx" ON "Post"("status", "published_at" DESC);

-- CreateIndex
CREATE INDEX "Post_featured_tier_featured_order_idx" ON "Post"("featured_tier", "featured_order");

-- CreateIndex
CREATE INDEX "Post_category_id_published_at_idx" ON "Post"("category_id", "published_at" DESC);

-- CreateIndex
CREATE INDEX "Comment_post_id_parent_id_status_created_at_idx" ON "Comment"("post_id", "parent_id", "status", "created_at");

-- CreateIndex
CREATE INDEX "Comment_parent_id_created_at_idx" ON "Comment"("parent_id", "created_at");

-- CreateIndex
CREATE INDEX "PostView_post_id_occurred_at_idx" ON "PostView"("post_id", "occurred_at" DESC);

-- CreateIndex
CREATE INDEX "PostView_occurred_at_idx" ON "PostView"("occurred_at" DESC);

-- CreateIndex
CREATE INDEX "SearchQuery_occurred_at_idx" ON "SearchQuery"("occurred_at" DESC);

-- CreateIndex
CREATE INDEX "SearchQuery_query_idx" ON "SearchQuery"("query");

-- CreateIndex
CREATE UNIQUE INDEX "AdSlot_key_key" ON "AdSlot"("key");

-- CreateIndex
CREATE INDEX "AdCreative_slot_id_active_starts_at_ends_at_idx" ON "AdCreative"("slot_id", "active", "starts_at", "ends_at");

-- CreateIndex
CREATE INDEX "AdEvent_creative_id_kind_occurred_at_idx" ON "AdEvent"("creative_id", "kind", "occurred_at");

-- CreateIndex
CREATE UNIQUE INDEX "RssSource_feed_url_key" ON "RssSource"("feed_url");

-- CreateIndex
CREATE INDEX "RssSource_active_last_fetched_at_idx" ON "RssSource"("active", "last_fetched_at");

-- CreateIndex
CREATE UNIQUE INDEX "ScrapedStory_url_key" ON "ScrapedStory"("url");

-- CreateIndex
CREATE UNIQUE INDEX "ScrapedStory_url_hash_key" ON "ScrapedStory"("url_hash");

-- CreateIndex
CREATE INDEX "ScrapedStory_scraped_at_idx" ON "ScrapedStory"("scraped_at" DESC);

-- CreateIndex
CREATE INDEX "ScrapedStory_status_scraped_at_idx" ON "ScrapedStory"("status", "scraped_at" DESC);

-- CreateIndex
CREATE INDEX "ScrapedStory_content_hash_idx" ON "ScrapedStory"("content_hash");

-- CreateIndex
CREATE UNIQUE INDEX "NewsletterRun_previous_run_id_key" ON "NewsletterRun"("previous_run_id");

-- CreateIndex
CREATE INDEX "NewsletterRun_target_date_idx" ON "NewsletterRun"("target_date" DESC);

-- CreateIndex
CREATE UNIQUE INDEX "NewsletterRun_target_date_key" ON "NewsletterRun"("target_date");

-- CreateIndex
CREATE UNIQUE INDEX "StorySelection_post_id_key" ON "StorySelection"("post_id");

-- CreateIndex
CREATE INDEX "StorySelection_run_id_rank_idx" ON "StorySelection"("run_id", "rank");

-- CreateIndex
CREATE INDEX "PromptTemplate_key_active_idx" ON "PromptTemplate"("key", "active");

-- CreateIndex
CREATE UNIQUE INDEX "PromptTemplate_key_version_key" ON "PromptTemplate"("key", "version");

-- CreateIndex
CREATE UNIQUE INDEX "Setting_key_key" ON "Setting"("key");

-- AddForeignKey
ALTER TABLE "Post" ADD CONSTRAINT "Post_author_id_fkey" FOREIGN KEY ("author_id") REFERENCES "Author"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Post" ADD CONSTRAINT "Post_category_id_fkey" FOREIGN KEY ("category_id") REFERENCES "Category"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Post" ADD CONSTRAINT "Post_newsletter_run_id_fkey" FOREIGN KEY ("newsletter_run_id") REFERENCES "NewsletterRun"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Comment" ADD CONSTRAINT "Comment_post_id_fkey" FOREIGN KEY ("post_id") REFERENCES "Post"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Comment" ADD CONSTRAINT "Comment_author_id_fkey" FOREIGN KEY ("author_id") REFERENCES "Author"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Comment" ADD CONSTRAINT "Comment_parent_id_fkey" FOREIGN KEY ("parent_id") REFERENCES "Comment"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PostView" ADD CONSTRAINT "PostView_post_id_fkey" FOREIGN KEY ("post_id") REFERENCES "Post"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AdCreative" ADD CONSTRAINT "AdCreative_slot_id_fkey" FOREIGN KEY ("slot_id") REFERENCES "AdSlot"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AdEvent" ADD CONSTRAINT "AdEvent_creative_id_fkey" FOREIGN KEY ("creative_id") REFERENCES "AdCreative"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AdEvent" ADD CONSTRAINT "AdEvent_post_id_fkey" FOREIGN KEY ("post_id") REFERENCES "Post"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ScrapedStory" ADD CONSTRAINT "ScrapedStory_source_id_fkey" FOREIGN KEY ("source_id") REFERENCES "RssSource"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "NewsletterRun" ADD CONSTRAINT "NewsletterRun_previous_run_id_fkey" FOREIGN KEY ("previous_run_id") REFERENCES "NewsletterRun"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "StorySelection" ADD CONSTRAINT "StorySelection_run_id_fkey" FOREIGN KEY ("run_id") REFERENCES "NewsletterRun"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "StorySelection" ADD CONSTRAINT "StorySelection_scraped_story_id_fkey" FOREIGN KEY ("scraped_story_id") REFERENCES "ScrapedStory"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "StorySelection" ADD CONSTRAINT "StorySelection_post_id_fkey" FOREIGN KEY ("post_id") REFERENCES "Post"("id") ON DELETE SET NULL ON UPDATE CASCADE;
