FROM node:22-bookworm

# Install Chrome dependencies + ffmpeg for Remotion rendering
RUN apt-get update && apt-get install -y \
    chromium \
    ffmpeg \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Set Chrome path for Remotion
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV REMOTION_CHROME_EXECUTABLE=/usr/bin/chromium

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci --production=false

# Copy source
COPY . .

# Build frontend
RUN npm run build

# Expose port
EXPOSE 3000
ENV PORT=3000
ENV NODE_ENV=production

CMD ["node", "server.js"]
