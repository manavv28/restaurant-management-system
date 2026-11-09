-- Additive migration; apply after 001. No existing data is deleted.
CREATE TABLE catalog_sources (
	id SERIAL NOT NULL,
	kind VARCHAR(30) NOT NULL,
	url TEXT NOT NULL,
	restaurant_id INTEGER,
	area VARCHAR(80) NOT NULL,
	permission_note TEXT NOT NULL,
	enabled BOOLEAN NOT NULL,
	refresh_hours INTEGER NOT NULL,
	checked_at VARCHAR(40),
	PRIMARY KEY (id),
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id)
)
;
CREATE TABLE payment_orders (
	id SERIAL NOT NULL,
	provider_order_id VARCHAR(100) NOT NULL,
	user_id INTEGER NOT NULL,
	restaurant_id INTEGER NOT NULL,
	amount_paise INTEGER NOT NULL,
	state VARCHAR(20) NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (provider_order_id),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id)
)
;
CREATE INDEX ix_payment_orders_user_id ON payment_orders (user_id);
CREATE TABLE search_matches (
	id SERIAL NOT NULL,
	search_id INTEGER NOT NULL,
	restaurant_id INTEGER NOT NULL,
	menu_item_id INTEGER NOT NULL,
	price_paise INTEGER NOT NULL,
	distance_km FLOAT NOT NULL,
	source TEXT NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(search_id) REFERENCES searches (id) ON DELETE CASCADE,
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id),
	FOREIGN KEY(menu_item_id) REFERENCES menu_items (id)
)
;
CREATE INDEX ix_search_matches_search_id ON search_matches (search_id);
CREATE TABLE catalog_jobs (
	id SERIAL NOT NULL,
	source_id INTEGER NOT NULL,
	state VARCHAR(20) NOT NULL,
	attempts INTEGER NOT NULL,
	available_at VARCHAR(40) NOT NULL,
	started_at VARCHAR(40),
	finished_at VARCHAR(40),
	trace TEXT NOT NULL,
	error TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY(source_id) REFERENCES catalog_sources (id)
)
;
CREATE INDEX ix_catalog_jobs_state ON catalog_jobs (state);
CREATE INDEX ix_catalog_jobs_source_id ON catalog_jobs (source_id);
CREATE UNIQUE INDEX catalog_one_active_job_per_source ON catalog_jobs (source_id) WHERE state IN ('queued', 'running');
CREATE TABLE menu_evidence (
	menu_item_id INTEGER NOT NULL,
	source_id INTEGER NOT NULL,
	excerpt TEXT NOT NULL,
	content_hash VARCHAR(64) NOT NULL,
	method VARCHAR(40) NOT NULL,
	fetched_at VARCHAR(40) NOT NULL,
	expires_at VARCHAR(40) NOT NULL,
	active BOOLEAN NOT NULL,
	PRIMARY KEY (menu_item_id),
	FOREIGN KEY(menu_item_id) REFERENCES menu_items (id),
	FOREIGN KEY(source_id) REFERENCES catalog_sources (id)
)
;
CREATE INDEX ix_menu_evidence_expires_at ON menu_evidence (expires_at);
ALTER TABLE public.catalog_sources ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.catalog_sources FROM anon, authenticated;
ALTER TABLE public.catalog_jobs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.catalog_jobs FROM anon, authenticated;
ALTER TABLE public.menu_evidence ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.menu_evidence FROM anon, authenticated;
ALTER TABLE public.search_matches ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.search_matches FROM anon, authenticated;
ALTER TABLE public.payment_orders ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.payment_orders FROM anon, authenticated;
