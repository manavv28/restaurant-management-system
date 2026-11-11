-- Additive product/analytics/account-security fields; preserve existing records.
ALTER TABLE public.users ADD COLUMN email_verified boolean NOT NULL DEFAULT false;
ALTER TABLE public.restaurants ADD COLUMN review_count integer;
ALTER TABLE public.restaurants ADD COLUMN image_url text NOT NULL DEFAULT '';
ALTER TABLE public.restaurants ADD COLUMN image_attribution text NOT NULL DEFAULT '';
ALTER TABLE public.restaurants ADD COLUMN ordering_url text NOT NULL DEFAULT '';
ALTER TABLE public.restaurants ADD COLUMN ownership_verified boolean NOT NULL DEFAULT false;
ALTER TABLE public.interactions ADD COLUMN search_id integer REFERENCES public.searches(id) ON DELETE SET NULL;
CREATE INDEX ix_interactions_search_id ON public.interactions(search_id);
CREATE UNIQUE INDEX one_attributed_click_per_match ON public.interactions(search_id,restaurant_id) WHERE search_id IS NOT NULL;
CREATE TABLE public.security_tokens (
 id varchar(64) PRIMARY KEY,
 user_id integer NOT NULL REFERENCES public.users(id),
 purpose varchar(30) NOT NULL,
 expires_at varchar(40) NOT NULL
);
CREATE INDEX ix_security_tokens_user_id ON public.security_tokens(user_id);
CREATE INDEX ix_security_tokens_expires_at ON public.security_tokens(expires_at);
CREATE TABLE public.rate_limits (key varchar(64) PRIMARY KEY, attempts integer NOT NULL, expires_at varchar(40) NOT NULL);
CREATE INDEX ix_rate_limits_expires_at ON public.rate_limits(expires_at);
CREATE TABLE public.ownership_proofs (
 restaurant_id integer PRIMARY KEY REFERENCES public.restaurants(id),
 token_hash varchar(64) NOT NULL,
 hostname varchar(254) NOT NULL,
 expires_at varchar(40) NOT NULL,
 verified_at varchar(40)
);
ALTER TABLE public.security_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rate_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ownership_proofs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.security_tokens,public.rate_limits,public.ownership_proofs FROM PUBLIC,anon,authenticated;
