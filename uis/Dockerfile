FROM node:20-alpine AS deps-backoffice
WORKDIR /app/uis/backoffice
COPY uis/backoffice/package.json uis/backoffice/package-lock.json ./
RUN npm ci

FROM node:20-alpine AS deps-website
WORKDIR /app/uis/website
COPY uis/website/package.json uis/website/package-lock.json ./
RUN npm ci

FROM node:20-alpine AS build-backoffice
WORKDIR /app/uis/backoffice
COPY --from=deps-backoffice /app/uis/backoffice/node_modules ./node_modules
COPY uis/backoffice/ ./
COPY src /app/src
RUN npm run build

FROM node:20-alpine AS build-website
WORKDIR /app/uis/website
COPY --from=deps-website /app/uis/website/node_modules ./node_modules
COPY uis/website/ ./
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=build-backoffice /app/uis/backoffice ./uis/backoffice
COPY --from=build-website /app/uis/website ./uis/website
COPY uis/start.sh ./start.sh

RUN chmod +x ./start.sh

EXPOSE 3000
EXPOSE 3001

CMD ["./start.sh"]
