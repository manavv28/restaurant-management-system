# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=secret,id=proxy_ca     if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca; fi;     npm ci --strict-ssl=true
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1
ENV API_INTERNAL_URL=http://127.0.0.1:8000
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
RUN --mount=type=secret,id=system_ca     apt-get update && apt-get install -y --no-install-recommends libstdc++6 ca-certificates &&     rm -rf /var/lib/apt/lists/*
COPY --from=frontend /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN --mount=type=secret,id=system_ca     if [ -f /run/secrets/system_ca ]; then export PIP_CERT=/run/secrets/system_ca; fi;     pip install --no-cache-dir -r backend/requirements.txt
COPY backend/app ./backend/app
COPY --from=frontend /build/frontend/.next/standalone ./frontend
COPY --from=frontend /build/frontend/.next/static ./frontend/.next/static
COPY scripts/production.py ./scripts/production.py
RUN useradd --uid 10001 --create-home biteai && chown -R biteai:biteai /app
USER biteai
ENV APP_ENV=production     HOSTNAME=0.0.0.0     PORT=10000     NEXT_TELEMETRY_DISABLED=1     ENABLE_PAYMENT_SIMULATION=false
EXPOSE 10000
CMD ["python", "scripts/production.py"]
