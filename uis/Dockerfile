FROM node:20-alpine AS deps-website
WORKDIR /app/website
COPY website/package.json website/package-lock.json ./
RUN npm ci

FROM node:20-alpine AS deps-backoffice
WORKDIR /app/backoffice
COPY backoffice/package.json backoffice/package-lock.json ./
RUN npm ci

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=development

COPY --from=deps-website /app/website/node_modules ./uis/website/node_modules
COPY --from=deps-backoffice /app/backoffice/node_modules ./uis/backoffice/node_modules
COPY website ./uis/website
COPY backoffice ./uis/backoffice
COPY start.sh ./start.sh

RUN chmod +x ./start.sh

EXPOSE 3000
EXPOSE 3001

CMD ["./start.sh"]
