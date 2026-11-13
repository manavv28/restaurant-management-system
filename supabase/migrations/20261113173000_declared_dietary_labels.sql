-- Preserve existing declarations while allowing explicit combined requirements.
-- Deploy before the API version that accepts vegan/gluten-free owner labels.
ALTER TABLE public.menu_items ALTER COLUMN dietary TYPE varchar(80);
ALTER TABLE public.menu_items DROP CONSTRAINT IF EXISTS menu_dietary_fact;
ALTER TABLE public.menu_items ADD CONSTRAINT menu_dietary_fact CHECK (
    dietary IS NULL OR dietary ~ '^(vegetarian|jain|halal|vegan|gluten-free)(,(vegetarian|jain|halal|vegan|gluten-free))*$'
);
