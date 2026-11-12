-- Existing owner/publisher menu rows retain NULL import keys and their provenance.
ALTER TABLE public.menu_items ADD COLUMN source_key varchar(96);
ALTER TABLE public.menu_items ADD CONSTRAINT menu_items_source_key_key UNIQUE (source_key);
-- One reviewed public-API menu feed per restaurant; other source kinds are unchanged.
CREATE UNIQUE INDEX ux_catalog_sources_indiarestros_restaurant
ON public.catalog_sources (restaurant_id) WHERE kind='indiarestros_api';
