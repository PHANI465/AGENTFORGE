# Build context is the repo root (see infra/docker/docker-compose.yml),
# same convention as every other service's Dockerfile.
FROM golang:1.22-alpine AS build

WORKDIR /app
COPY services/auth-service/go.mod services/auth-service/go.sum* ./
RUN go mod download

COPY services/auth-service/. .
RUN CGO_ENABLED=0 go build -o /auth-service .

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=build /auth-service /auth-service

EXPOSE 8004
ENTRYPOINT ["/auth-service"]
