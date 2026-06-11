FROM node:20-alpine AS base

WORKDIR /app
RUN apk add --no-cache libc6-compat

# ─── DEVELOPMENT ────────────────────────────────────────────
FROM base AS development
ENV NODE_ENV=development
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# ─── BUILDER ────────────────────────────────────────────────
FROM base AS builder
COPY package*.json ./
RUN npm ci
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
# next.config.js rewrites() se evalúan en BUILD time y se hornean en el
# routes-manifest. BACKEND_INTERNAL_URL debe existir acá (no en runtime) para
# que el proxy /api/v1/* apunte a http://api:8000 y no al fallback localhost.
ARG BACKEND_INTERNAL_URL=http://api:8000
ENV BACKEND_INTERNAL_URL=$BACKEND_INTERNAL_URL
RUN npm run build

# ─── PRODUCTION ─────────────────────────────────────────────
FROM base AS production
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
