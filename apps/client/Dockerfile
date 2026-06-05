FROM node:24-alpine AS builder

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/client/package.json ./apps/client/package.json
RUN pnpm install --frozen-lockfile --filter @task-orchestrator/client... --ignore-scripts

COPY apps/client ./apps/client
WORKDIR /app/apps/client
RUN pnpm build

FROM nginx:1.29-alpine

COPY apps/client/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/client/dist /usr/share/nginx/html

EXPOSE 80
