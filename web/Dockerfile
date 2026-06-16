FROM node:20-alpine AS builder

WORKDIR /app

# Enable Corepack so the yarn version in package.json is respected
RUN corepack enable

COPY package.json yarn.lock .yarnrc.yml ./
RUN yarn install --immutable

COPY . .

ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN yarn build

# ─────────────────────────────────────────────
FROM nginx:alpine AS production

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
