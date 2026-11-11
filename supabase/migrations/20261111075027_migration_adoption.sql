-- A single checksum ledger is used by app.cloud_run migrate for subsequent releases.
-- Existing manually initialized projects may adopt only after schema verification.
CREATE TABLE IF NOT EXISTS public.biteai_migrations (name text PRIMARY KEY, sha256 text NOT NULL);
ALTER TABLE public.biteai_migrations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.biteai_migrations FROM PUBLIC, anon, authenticated;
