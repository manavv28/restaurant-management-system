-- Preserve cross-provider identities and provenance; all access is via the backend.
CREATE TABLE public.catalog_identities (
    provider varchar(32) NOT NULL,
    external_id varchar(200) NOT NULL,
    restaurant_id integer NOT NULL REFERENCES public.restaurants(id),
    source_url text NOT NULL,
    licence text NOT NULL,
    observed_at varchar(40) NOT NULL,
    details text NOT NULL,
    PRIMARY KEY (provider, external_id)
);
CREATE INDEX ix_catalog_identities_restaurant_id ON public.catalog_identities (restaurant_id);
ALTER TABLE public.catalog_identities ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.catalog_identities FROM PUBLIC, anon, authenticated;
