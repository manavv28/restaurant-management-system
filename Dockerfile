# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS frontend
ARG NEXT_PUBLIC_GOOGLE_MAPS_KEY=
ARG NEXT_PUBLIC_GOOGLE_MAP_ID=
ENV NEXT_TELEMETRY_DISABLED=1 API_INTERNAL_URL=http://127.0.0.1:8000 \
    NEXT_PUBLIC_GOOGLE_MAPS_KEY=$NEXT_PUBLIC_GOOGLE_MAPS_KEY NEXT_PUBLIC_GOOGLE_MAP_ID=$NEXT_PUBLIC_GOOGLE_MAP_ID
# Bind source and discard build dependencies within one layer. This keeps VFS builders
# from copying an entire node_modules tree for every COPY/RUN instruction.
RUN --mount=type=bind,source=frontend,target=/src,readonly \
    --mount=type=secret,id=proxy_ca \
    set -eu; \
    if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca; fi; \
    mkdir -p /build; cp -a /src/. /build/; cd /build; \
    npm ci --strict-ssl=true; npm run build; \
    mkdir -p /out/.next; cp -a .next/standalone/. /out/; \
    cp -a .next/static /out/.next/static; \
    rm -rf /build /root/.npm

FROM python:3.12-slim-bookworm AS runtime
COPY --from=frontend /usr/local/bin/node /usr/local/bin/node
ARG DATABASE_CA_SOURCE=official
RUN --mount=type=bind,source=.,target=/src,readonly \
    --mount=type=secret,id=system_ca --mount=type=secret,id=supabase_ca \
    set -eu; \
    apt-get update; apt-get install -y --no-install-recommends libstdc++6 ca-certificates openssl poppler-utils tesseract-ocr tesseract-ocr-eng util-linux; \
    rm -rf /var/lib/apt/lists/*; \
    if [ -f /run/secrets/system_ca ]; then export PIP_CERT=/run/secrets/system_ca SSL_CERT_FILE=/run/secrets/system_ca; fi; \
    pip install --no-cache-dir -r /src/backend/requirements.txt; \
    mkdir -p /app/backend /app/scripts; \
    cp -a /src/backend/app /app/backend/app; \
    cp -a /src/supabase/migrations /app/migrations; \
    cp /src/scripts/production.py /app/scripts/production.py; \
    if [ "$DATABASE_CA_SOURCE" = official ]; then PYTHONPATH=/app/backend python -m app.build_database_ca; \
    elif [ "$DATABASE_CA_SOURCE" = operator ]; then PYTHONPATH=/app/backend python -m app.build_database_ca --certificate-file /run/secrets/supabase_ca; \
    else exit 1; fi; \
    useradd --uid 10001 --create-home biteai; chown -R biteai:biteai /app
COPY --from=frontend --chown=10001:10001 /out /app/frontend
WORKDIR /app
USER biteai
ENV APP_ENV=production HOSTNAME=0.0.0.0 PORT=10000 NEXT_TELEMETRY_DISABLED=1 \
    AUTO_CREATE_SCHEMA=false SEED_SAMPLE_DATA=false ENABLE_PAYMENT_SIMULATION=false
EXPOSE 10000
CMD ["python", "scripts/production.py"]
