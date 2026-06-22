FROM node:20-alpine

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./

RUN npm install

COPY frontend .

RUN npm run build

EXPOSE 5174

CMD ["npm", "run", "preview", "--", "--host"]
