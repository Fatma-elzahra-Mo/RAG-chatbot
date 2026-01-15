# Docker Deployment Guide

## Quick Start

### Prerequisites
- Docker (20.10+)
- Docker Compose (2.0+)
- 8GB RAM minimum
- OpenAI API Key

### 1. Clone and Setup

```bash
git clone <repository-url>
cd arabic-rag-chatbot
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```bash
OPENAI_API_KEY=sk-your-actual-key-here
```

### 2. Deploy

```bash
# Using the deployment script (recommended)
./scripts/deploy.sh

# OR manually with docker-compose
docker-compose up -d
```

### 3. Verify Deployment

```bash
# Check all services are healthy
docker-compose ps

# Check API health
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs
```

### 4. Ingest Sample Data

```bash
./scripts/ingest_sample_data.sh
```

### 5. Test the Chatbot

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "ما هي عاصمة مصر؟"}'
```

---

## Service Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Docker Network                        │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Qdrant     │  │    Redis     │  │  PostgreSQL  │ │
│  │  (Vectors)   │  │   (Cache)    │  │    (Logs)    │ │
│  │   :6333      │  │    :6379     │  │    :5432     │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                 │                  │         │
│         └────────┬────────┴──────────────────┘         │
│                  │                                      │
│         ┌────────▼─────────┐                           │
│         │  Chatbot API     │                           │
│         │  (FastAPI)       │                           │
│         │    :8000         │                           │
│         └──────────────────┘                           │
└─────────────────────────────────────────────────────────┘
```

## Services

### Chatbot API
- **Port**: 8000
- **Image**: Built from Dockerfile
- **Health**: `http://localhost:8000/health`
- **Docs**: `http://localhost:8000/docs`

### Qdrant Vector Database
- **Port**: 6333 (HTTP), 6334 (gRPC)
- **Image**: `qdrant/qdrant:v1.11.3`
- **Dashboard**: `http://localhost:6333/dashboard`

### Redis Cache
- **Port**: 6379
- **Image**: `redis:7-alpine`

### PostgreSQL Database
- **Port**: 5432
- **Image**: `postgres:16-alpine`
- **Database**: chatbot
- **User**: chatbot

---

## Development Mode

For development with hot-reload:

```bash
# Start with development overrides
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# OR using Make
make docker-dev
```

Features in dev mode:
- Source code mounted for hot-reload
- Debug logging enabled
- Faster health checks

---

## Common Operations

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f chatbot
docker-compose logs -f qdrant
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart chatbot
```

### Stop Services

```bash
# Stop without removing volumes
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove everything including volumes
docker-compose down -v
```

### Rebuild After Code Changes

```bash
# Rebuild and restart
docker-compose up -d --build

# OR
make docker-build
make docker-up
```

### Access Service Shells

```bash
# Chatbot API
docker-compose exec chatbot bash

# Qdrant
docker-compose exec qdrant sh

# Redis CLI
docker-compose exec redis redis-cli

# PostgreSQL
docker-compose exec postgres psql -U chatbot -d chatbot
```

---

## Data Persistence

All data is persisted in Docker volumes:

```bash
# List volumes
docker volume ls | grep arabic-rag

# Inspect volume
docker volume inspect arabic-rag-chatbot_qdrant_data

# Backup Qdrant data
docker run --rm -v arabic-rag-chatbot_qdrant_data:/source -v $(pwd)/backups:/backup alpine tar czf /backup/qdrant-backup.tar.gz -C /source .

# Restore Qdrant data
docker run --rm -v arabic-rag-chatbot_qdrant_data:/target -v $(pwd)/backups:/backup alpine tar xzf /backup/qdrant-backup.tar.gz -C /target
```

---

## Environment Variables

### Required
- `OPENAI_API_KEY`: Your OpenAI API key

### Optional
- `ENVIRONMENT`: production/development (default: production)
- `LOG_LEVEL`: DEBUG/INFO/WARNING/ERROR (default: INFO)
- `POSTGRES_PASSWORD`: PostgreSQL password (default: chatbot123)

See `.env.example` for all available options.

---

## Monitoring

### Health Checks

All services have health checks configured:

```bash
# Check service health
docker-compose ps

# Service-specific health checks
curl http://localhost:8000/health        # API
curl http://localhost:6333/healthz       # Qdrant
docker-compose exec redis redis-cli ping # Redis
```

### Resource Usage

```bash
# View resource usage
docker stats

# View by service
docker stats arabic-rag-api arabic-rag-qdrant arabic-rag-redis arabic-rag-postgres
```

---

## Troubleshooting

### API Won't Start

```bash
# Check logs
docker-compose logs chatbot

# Common issues:
# 1. Missing OPENAI_API_KEY
# 2. Qdrant/Redis not healthy
# 3. Port 8000 already in use
```

### Qdrant Connection Errors

```bash
# Check Qdrant is running
curl http://localhost:6333/healthz

# Check network
docker network inspect arabic-rag-chatbot_chatbot-network
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Change port in .env
API_PORT=8001

# Or modify docker-compose.yml
ports:
  - "8001:8000"
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Increase Docker memory limit (Docker Desktop)
# Settings > Resources > Memory > 8GB+

# Or reduce batch sizes in .env
EMBEDDINGS_BATCH_SIZE=16
```

---

## Production Deployment

### Security Checklist

- [ ] Change default PostgreSQL password
- [ ] Enable API key authentication
- [ ] Configure CORS origins
- [ ] Use secrets management (not .env)
- [ ] Enable HTTPS/TLS
- [ ] Set up monitoring/alerting
- [ ] Configure log rotation
- [ ] Regular backups
- [ ] Resource limits in docker-compose

### Example Production Config

```yaml
# docker-compose.prod.yml
services:
  chatbot:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"
```

### Using with Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## CI/CD Integration

GitHub Actions workflow included in `.github/workflows/ci.yml`:

- Runs tests on push/PR
- Builds and tests Docker image
- Integration tests with Qdrant/Redis
- Coverage reporting

To run locally:

```bash
# Install dependencies
make install

# Run tests
make test

# Run linting
make lint

# Build Docker
make docker-build
```

---

## Makefile Commands

```bash
make help           # Show all commands
make install        # Install dependencies
make test           # Run tests
make lint           # Run linters
make format         # Format code
make docker-build   # Build Docker image
make docker-up      # Start services
make docker-down    # Stop services
make docker-logs    # View logs
make ingest         # Ingest sample data
make clean          # Clean artifacts
```

---

## Support

For issues and questions:
- Check logs: `docker-compose logs -f`
- GitHub Issues: <repository-url>/issues
- Documentation: `http://localhost:8000/docs`
