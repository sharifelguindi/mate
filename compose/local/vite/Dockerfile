FROM node:20-alpine

WORKDIR /app/frontend

# Install build dependencies
RUN apk add --no-cache python3 make g++

# Copy start script
COPY ./compose/local/vite/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

# Don't copy or install anything else - let the start script handle it

EXPOSE 3000

CMD ["/start"]