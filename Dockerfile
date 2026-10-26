FROM docker.io/library/alpine:3 AS compress
RUN apk add --no-cache gzip findutils python3
COPY output /srv/archive
COPY scripts/generate_reply_redirects.py /generate_reply_redirects.py
RUN python3 /generate_reply_redirects.py /srv/archive /reply-redirects.map
RUN find /srv/archive -type f -size +1k \
      \( -name '*.html' -o -name '*.css' -o -name '*.js' -o -name '*.json' -o -name '*.svg' -o -name '*.xml' -o -name '*.txt' \) \
      -exec gzip -9 -k -n {} +

FROM ghcr.io/nginx/nginx-unprivileged:stable-alpine-slim
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=compress /reply-redirects.map /etc/nginx/reply-redirects.map
COPY --from=compress /srv/archive /srv/archive
