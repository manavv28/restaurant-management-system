-- Additive upgrade for the existing 001 + 002 schema. Existing accounts are preserved.
-- Legacy JWTs have no revocable session and require one fresh sign-in after this release.
CREATE TABLE public.auth_sessions (
    id varchar(64) PRIMARY KEY,
    user_id integer NOT NULL REFERENCES public.users(id),
    expires_at varchar(40) NOT NULL
);
CREATE INDEX ix_auth_sessions_user_id ON public.auth_sessions (user_id);
CREATE INDEX ix_auth_sessions_expires_at ON public.auth_sessions (expires_at);
ALTER TABLE public.auth_sessions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.auth_sessions FROM PUBLIC, anon, authenticated;

-- Supabase's optional auto-RLS event trigger is internal DDL infrastructure.
-- Preserve the trigger and revoke only its unnecessary public RPC privileges.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname='public' AND p.proname='rls_auto_enable'
          AND p.pronargs=0 AND p.prorettype='event_trigger'::regtype
    ) THEN
        REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated;
    END IF;
END
$$;
