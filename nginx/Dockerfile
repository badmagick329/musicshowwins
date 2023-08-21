FROM nginx:latest
RUN apt-get update && apt-get install -y procps
RUN rm /etc/nginx/conf.d/default.conf
RUN mkdir -p /etc/nginx/ssl
RUN mkdir -p /usr/src/app
