FROM node:20-bullseye

# Install Python for Python scripts
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Node dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the project
COPY . .

EXPOSE 3000
CMD ["node", "server.js"]
