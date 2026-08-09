-- Review this migration with the database owner before applying it.
-- It is intentionally not executed automatically by the application.

BEGIN;

ALTER TABLE public."Route"
    ADD COLUMN IF NOT EXISTS "EncodedPolyline" TEXT,
    ADD COLUMN IF NOT EXISTS "Steps" JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS "CreatedAt" TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_route_created_at
    ON public."Route" ("CreatedAt" DESC);

COMMIT;
