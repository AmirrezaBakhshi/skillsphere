# syntax=docker/dockerfile:1
FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm config set registry https://registry.npmmirror.com
RUN npm install --verbose

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
