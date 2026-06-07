FROM node:22-alpine AS build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@10.12.4 --activate

COPY pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY apps/web apps/web
RUN pnpm --dir apps/web install --frozen-lockfile
RUN pnpm --dir apps/web build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN corepack enable && corepack prepare pnpm@10.12.4 --activate

COPY --from=build /app ./
WORKDIR /app/apps/web
EXPOSE 3000
CMD ["pnpm", "start"]
