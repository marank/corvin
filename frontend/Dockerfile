FROM node:26-alpine AS build
# Node 25+ no longer ships corepack; it installs pnpm in the version of the
# "packageManager" field in package.json.
RUN npm install --global corepack@0.36.0 && corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

# Runs as the unprivileged "nginx" user (uid 101) on port 8080.
FROM nginxinc/nginx-unprivileged:alpine
USER root
# Security fixes Alpine published after the base image was built.
RUN apk upgrade --no-cache
USER 101
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --chmod=755 docker/40-trusted-proxies.sh /docker-entrypoint.d/
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:8080/ || exit 1
