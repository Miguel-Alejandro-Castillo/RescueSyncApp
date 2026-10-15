FROM node:22

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

# Generar cliente de Prisma
RUN npx prisma generate

EXPOSE 4000

# Convertir finales de línea de Windows a Unix y dar permisos de ejecución al script start.sh
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

# Usar este comando para producción
# CMD ["npm", "start"]
# Usar este comando para desarrollo
# CMD ["./start.sh"]
CMD ["sh", "./start.sh"] 