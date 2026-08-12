# Build context is dashboard/ itself (see infra/docker/docker-compose.yml) —
# this is a standalone npm project, not part of the Python uv workspace.
FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
