# Supabase database trust bundle

The Docker build runs app.build_database_ca to download the public production CA over
verified HTTPS from Supabase's official distribution URL and append it to the
image's system trust roots. It validates certificate syntax, CA constraints and
remaining validity, then writes supabase-bundle.pem and a source/SHA256 manifest.
No API key or dashboard-uploaded Secret File is needed.

Authoritative source: supabase/supabase repository, commit
4c686101671fa512225575b44a7b08ff66538780:
- apps/studio/components/interfaces/Settings/Database/SSLConfiguration.tsx selects prod.
- apps/studio/hooks/custom-content/custom-content.json defines ssl:certificate_url:
  https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/${env}/ssl/${env}-ca-2021.crt
- apps/docs/content/guides/platform/ssl-enforcement.mdx documents this CA for verify-full.

Runtime connections to official Supabase database hosts use this bundle and
verify-full. Custom readable CA paths are honoured. The missing legacy Secret File path and the earlier system-store path are replaced by the image's bundle automatically. A present explicitly uploaded certificate is preserved.
Unrelated PostgreSQL hosts retain their explicit TLS settings.

For local development with a live Supabase database:
    PYTHONPATH=backend .venv/bin/python -m app.build_database_ca
Generated bundles/manifests are build outputs and should not be committed.

An explicitly provided certificate file can be used for operator-controlled builds
or isolated tests. Test certificates must never be deployed as production trust roots.

Docker builds default to DATABASE_CA_SOURCE=official. Isolated fixture/operator builds must explicitly set --build-arg DATABASE_CA_SOURCE=operator and mount the supabase_ca build secret. The explicit argument separates build-cache keys so a fixture certificate cannot accidentally be reused by a default production build.
