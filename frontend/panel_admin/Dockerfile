FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
COPY tools/minimatch-compat/ ./tools/minimatch-compat/
RUN npm ci
COPY . .
ARG NG_BUILD_MAX_WORKERS=1
ARG NODE_OPTIONS="--max-old-space-size=1536"
RUN NG_BUILD_MAX_WORKERS="$NG_BUILD_MAX_WORKERS" NODE_OPTIONS="$NODE_OPTIONS" \
    npm run build -- --configuration production

FROM nginx:stable-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/oreva/browser/ /usr/share/nginx/html/
EXPOSE 80