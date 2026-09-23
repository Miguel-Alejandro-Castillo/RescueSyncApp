FROM node:22

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 5173

#CMD ["npm", "run", "dev", "--", "--host"]
# Se especifica 0.0.0.0 para evitar que escuche únicamente en 127.0.0.1 dentro del contenedor
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]