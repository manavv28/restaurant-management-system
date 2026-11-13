-- Cover the public coverage aggregates without visiting every wide menu/evidence row.
CREATE INDEX IF NOT EXISTS ix_menu_items_available_coverage
ON public.menu_items (id) INCLUDE (restaurant_id) WHERE available IS TRUE;
CREATE INDEX IF NOT EXISTS ix_menu_evidence_active_coverage
ON public.menu_evidence (menu_item_id) INCLUDE (expires_at) WHERE active IS TRUE;
CREATE INDEX IF NOT EXISTS ix_catalog_identities_observed_at
ON public.catalog_identities (observed_at);
