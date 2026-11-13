-- PRD concierge: explicit facts, private workflow data and safe test vouchers.

ALTER TABLE public.menu_items ADD COLUMN IF NOT EXISTS dietary varchar(20);

ALTER TABLE public.transactions ADD COLUMN IF NOT EXISTS test_mode boolean NOT NULL DEFAULT false;

ALTER TABLE public.transactions ADD COLUMN IF NOT EXISTS provider_order_id varchar(100);

CREATE INDEX IF NOT EXISTS ix_transactions_provider_order_id ON public.transactions(provider_order_id);

ALTER TABLE public.payment_orders ADD COLUMN IF NOT EXISTS test_mode boolean NOT NULL DEFAULT false;


CREATE TABLE campaign_policies (
	campaign_id INTEGER NOT NULL, 
	min_tier VARCHAR(20) NOT NULL, 
	cuisine VARCHAR(100) NOT NULL, 
	cuisine_queries_30d INTEGER NOT NULL, 
	daily_budget_paise INTEGER NOT NULL, 
	flat_discount_paise INTEGER NOT NULL, 
	PRIMARY KEY (campaign_id), 
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE
)

;

ALTER TABLE public.campaign_policies ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.campaign_policies FROM PUBLIC, anon, authenticated;


CREATE TABLE agent_runs (
	id VARCHAR(64) NOT NULL, 
	agent VARCHAR(30) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	search_id INTEGER, 
	summary TEXT NOT NULL, 
	latency_ms INTEGER NOT NULL, 
	cost_microrupees INTEGER, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(search_id) REFERENCES searches (id) ON DELETE SET NULL
)

;

CREATE INDEX ix_agent_runs_agent ON agent_runs (agent);

CREATE INDEX ix_agent_runs_search_id ON agent_runs (search_id);

CREATE INDEX ix_agent_runs_created_at ON agent_runs (created_at);

ALTER TABLE public.agent_runs ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.agent_runs FROM PUBLIC, anon, authenticated;


CREATE TABLE research_requests (
	id VARCHAR(64) NOT NULL, 
	search_id INTEGER, 
	job_ids TEXT NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(search_id) REFERENCES searches (id) ON DELETE SET NULL
)

;

CREATE INDEX ix_research_requests_created_at ON research_requests (created_at);

CREATE INDEX ix_research_requests_search_id ON research_requests (search_id);

ALTER TABLE public.research_requests ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.research_requests FROM PUBLIC, anon, authenticated;


CREATE TABLE bronze_artifacts (
	id VARCHAR(64) NOT NULL, 
	source_id INTEGER NOT NULL, 
	content_hash VARCHAR(64) NOT NULL, 
	content TEXT NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_id) REFERENCES catalog_sources (id)
)

;

CREATE INDEX ix_bronze_artifacts_created_at ON bronze_artifacts (created_at);

CREATE INDEX ix_bronze_artifacts_source_id ON bronze_artifacts (source_id);

ALTER TABLE public.bronze_artifacts ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.bronze_artifacts FROM PUBLIC, anon, authenticated;


CREATE TABLE deal_vouchers (
	id VARCHAR(64) NOT NULL, 
	payment_order_id INTEGER NOT NULL, 
	redemption_id INTEGER NOT NULL, 
	state VARCHAR(20) NOT NULL, 
	expires_at VARCHAR(40) NOT NULL, 
	redeemed_at VARCHAR(40), 
	PRIMARY KEY (id), 
	UNIQUE (payment_order_id), 
	FOREIGN KEY(payment_order_id) REFERENCES payment_orders (id), 
	UNIQUE (redemption_id), 
	FOREIGN KEY(redemption_id) REFERENCES redemptions (id)
)

;

CREATE INDEX ix_deal_vouchers_expires_at ON deal_vouchers (expires_at);

ALTER TABLE public.deal_vouchers ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.deal_vouchers FROM PUBLIC, anon, authenticated;


CREATE TABLE restaurant_claims (
	id VARCHAR(64) NOT NULL, 
	restaurant_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	business_reference VARCHAR(40) NOT NULL, 
	state VARCHAR(20) NOT NULL, 
	review_note TEXT NOT NULL, 
	reviewed_by INTEGER, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(reviewed_by) REFERENCES users (id)
)

;

CREATE INDEX ix_restaurant_claims_user_id ON restaurant_claims (user_id);

CREATE INDEX ix_restaurant_claims_restaurant_id ON restaurant_claims (restaurant_id);

ALTER TABLE public.restaurant_claims ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.restaurant_claims FROM PUBLIC, anon, authenticated;

ALTER TABLE public.menu_items ADD CONSTRAINT menu_dietary_fact CHECK (dietary IS NULL OR dietary IN ('vegetarian','jain','halal'));

ALTER TABLE public.campaign_policies ADD CONSTRAINT policy_values CHECK (min_tier IN ('Bronze','Silver','Gold','Platinum') AND daily_budget_paise > 0 AND cuisine_queries_30d BETWEEN 0 AND 100 AND flat_discount_paise >= 0);
