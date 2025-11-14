# Dockerfile para moodle-mcp-server
FROM node:20-slim

WORKDIR /app

COPY moodle-mcp-server/package.json moodle-mcp-server/package-lock.json ./
RUN npm install --omit=dev

COPY moodle-mcp-server ./

EXPOSE 3000

CMD ["node", "build/index.js"]
