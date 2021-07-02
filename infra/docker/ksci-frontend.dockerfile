FROM node:14.17.1 as build-deps
WORKDIR /app
COPY ksci-frontend/package.json ksci-frontend/yarn.lock ./
RUN yarn
COPY ksci-frontend/ ./
RUN yarn build

FROM nginx:1.21-alpine
COPY infra/docker/nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build-deps /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
