-- PostGIS is optional on ordinary PostgreSQL; Supabase provides the extension.
-- Install in an unexposed schema; keep latitude/longitude as the portable source of truth.
DO $$
DECLARE ext_schema text;
BEGIN
 IF EXISTS(SELECT 1 FROM pg_available_extensions WHERE name='postgis') THEN
  IF NOT EXISTS(SELECT 1 FROM pg_extension WHERE extname='postgis') THEN
   CREATE SCHEMA IF NOT EXISTS extensions;
   CREATE EXTENSION postgis WITH SCHEMA extensions;
  END IF;
  SELECT n.nspname INTO ext_schema FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='postgis';
  IF ext_schema IN ('extensions','public') THEN
   EXECUTE format('CREATE INDEX IF NOT EXISTS restaurants_geography_idx ON public.restaurants USING gist ((%I.st_setsrid(%I.st_makepoint(longitude,latitude),4326)::%I.geography))',ext_schema,ext_schema,ext_schema);
  END IF;
 END IF;
END
$$;
