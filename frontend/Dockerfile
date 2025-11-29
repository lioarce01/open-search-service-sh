# Build stage
FROM node:20-alpine as build

# Install pnpm
RUN npm install -g pnpm

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml* ./

# Install dependencies (update lockfile if needed)
RUN pnpm install

# Copy source code
COPY . .

# Build the app
RUN pnpm run build

# Production stage
FROM node:20-alpine as production

# Install pnpm
RUN npm install -g pnpm

WORKDIR /app

# Copy package files
COPY package.json ./
COPY --from=build /app/pnpm-lock.yaml ./

# Install only production dependencies (use frozen lockfile for reproducibility)
RUN pnpm install --frozen-lockfile --prod

# Copy built app from build stage
COPY --from=build /app/.next ./.next
COPY --from=build /app/public ./public
COPY --from=build /app/package.json ./

EXPOSE 3000

# Start the application
CMD ["pnpm", "start"]
