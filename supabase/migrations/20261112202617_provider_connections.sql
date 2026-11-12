-- Server-managed, encrypted, per-user provider credentials. Never expose via Data API.
CREATE TABLE public.provider_connections (
 user_id integer NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
 provider varchar(30) NOT NULL CHECK (provider IN ('swiggy','zomato')),
 encrypted_tokens text NOT NULL,
 tool_manifest text NOT NULL DEFAULT '[]',
 retain_until varchar(40) NOT NULL,
 expires_at varchar(40) NOT NULL,
 PRIMARY KEY(user_id,provider)
);
CREATE TABLE public.provider_oauth_states (
 id varchar(64) PRIMARY KEY,
 user_id integer NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
 session_id varchar(64) NOT NULL,
 encrypted_flow text NOT NULL,
 expires_at varchar(40) NOT NULL
);
CREATE INDEX ix_provider_oauth_states_user_id ON public.provider_oauth_states(user_id);
CREATE INDEX ix_provider_oauth_states_expires_at ON public.provider_oauth_states(expires_at);
ALTER TABLE public.provider_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.provider_oauth_states ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.provider_connections,public.provider_oauth_states FROM PUBLIC;
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN
  REVOKE ALL ON public.provider_connections,public.provider_oauth_states FROM anon;
 END IF;
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN
  REVOKE ALL ON public.provider_connections,public.provider_oauth_states FROM authenticated;
 END IF;
END $$;
