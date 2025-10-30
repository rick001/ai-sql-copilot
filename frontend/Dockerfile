FROM node:20-alpine
WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
RUN corepack enable && corepack prepare pnpm@9.11.0 --activate && pnpm install --frozen-lockfile || pnpm install
COPY . .
RUN pnpm build || true
EXPOSE 3000
CMD ["pnpm", "dev"]

