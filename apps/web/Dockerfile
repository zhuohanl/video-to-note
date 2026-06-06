FROM node:22-alpine AS deps
WORKDIR /app
RUN corepack enable
COPY pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm --dir apps/web install --frozen-lockfile

FROM node:22-alpine AS build
WORKDIR /app
RUN corepack enable
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules
COPY pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web apps/web
RUN pnpm --dir apps/web build

FROM node:22-alpine AS runner
WORKDIR /app/apps/web
ENV NODE_ENV=production
RUN corepack enable
COPY --from=build /app/apps/web ./
EXPOSE 3000
CMD ["pnpm", "start"]
