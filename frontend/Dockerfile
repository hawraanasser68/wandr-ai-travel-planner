# ── Stage 1: build the React app ──────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build
# Output is in /app/dist

# ── Stage 2: serve with nginx ─────────────────────────────────────────────────
FROM nginx:alpine

# Replace the default nginx config with ours (handles API proxying + SPA routing)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built React files
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
