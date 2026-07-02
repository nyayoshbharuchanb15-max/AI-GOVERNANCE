# ─── Stage 1: Build ───────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json tsconfig.json ./
RUN npm install
COPY src/ ./src/
RUN npm run build

# ─── Stage 2: Production ──────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app
RUN apk add --no-cache curl
COPY package.json ./
RUN npm install --production
COPY --from=builder /app/dist ./dist
EXPOSE 3000

# Healthcheck: SSE mode listens on 3000, stdio mode uses process health
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD sh -c 'if [ "$MCP_TRANSPORT" = "sse" ]; then curl -sf http://localhost:3000/health || exit 1; else pgrep -f "node dist/index.js" || exit 1; fi'

CMD ["node", "dist/index.js"]
