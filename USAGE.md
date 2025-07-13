# Docker Usage Guide

## Quick Start

### 1. Pull the image
```bash
docker pull ghcr.io/your-username/arxiv-autosumm:latest
```

### 2. Run with docker-compose (recommended)
```bash
# Clone the repository
git clone https://github.com/your-username/arxiv-autosumm.git
cd arxiv-autosumm

# Create directories
mkdir -p config cache output

# Copy and edit configuration
cp config.yaml config/config.yaml
# Edit config/config.yaml with your settings

# Run the pipeline
docker-compose up arxiv-autosumm

# Run with scheduling (daily at 3 AM)
docker-compose --profile scheduled up arxiv-autosumm-scheduled
```

### 3. Run with docker directly
```bash
# Single run
docker run --rm \
  -v $(pwd)/config:/data/config \
  -v $(pwd)/cache:/data/cache \
  -v $(pwd)/output:/data/output \
  ghcr.io/your-username/arxiv-autosumm:latest

# Interactive setup
docker run --rm -it \
  -v $(pwd)/config:/data/config \
  -v $(pwd)/cache:/data/cache \
  -v $(pwd)/output:/data/output \
  ghcr.io/your-username/arxiv-autosumm:latest init

# Test configuration
docker run --rm \
  -v $(pwd)/config:/data/config \
  -v $(pwd)/cache:/data/cache \
  -v $(pwd)/output:/data/output \
  ghcr.io/your-username/arxiv-autosumm:latest test-config
```

## Configuration

### Environment Variables
- `ARXIV_AUTOSUMM_CONFIG`: Path to config file (default: /data/config/config.yaml)
- `ARXIV_AUTOSUMM_CACHE_DIR`: Cache directory (default: /data/cache)
- `ARXIV_AUTOSUMM_OUTPUT_DIR`: Output directory (default: /data/output)

### Volume Mounts
- `/data/config`: Configuration files
- `/data/cache`: Persistent cache
- `/data/output`: Generated summaries

### Example Configuration
```yaml
# config/config.yaml
runtime:
  docker_mount_cache: /data/cache
  docker_mount_output: /data/output

fetch:
  days: 7
  max_results: 10
  
summarize:
  provider: openai
  api_key: "env:OPENAI_API_KEY"
  model: gpt-4

# ... rest of config
```

## Building from Source

### Local build
```bash
# Build the image
docker build -t arxiv-autosumm -f docker/Dockerfile .

# Run locally
docker run --rm -v $(pwd)/config:/data/config arxiv-autosumm
```

### Build with buildx
```bash
# Build multi-platform image
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t arxiv-autosumm:latest \
  -f docker/Dockerfile .
```

## Managing Data

### Persistent Volumes
```bash
# Create named volumes
docker volume create arxiv-config
docker volume create arxiv-cache
docker volume create arxiv-output

# Use with volumes
docker run --rm \
  -v arxiv-config:/data/config \
  -v arxiv-cache:/data/cache \
  -v arxiv-output:/data/output \
  arxiv-autosumm:latest
```

### Backup and Restore
```bash
# Backup
docker run --rm \
  -v arxiv-cache:/data/cache \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/cache-backup.tar.gz -C /data cache

# Restore
docker run --rm \
  -v arxiv-cache:/data/cache \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/cache-backup.tar.gz -C /
```

## Monitoring and Logs

### View logs
```bash
# Docker logs
docker logs arxiv-autosumm

# Docker-compose logs
docker-compose logs -f arxiv-autosumm
```

### Health checks
```bash
# Check if container is running
docker ps | grep arxiv-autosumm

# Check container health
docker inspect arxiv-autosumm --format='{{.State.Health.Status}}'
```

## Troubleshooting

### Common Issues

1. **Permission denied**: Ensure volumes have correct permissions
   ```bash
   sudo chown -R 1000:1000 config cache output
   ```

2. **Config file not found**: Mount config directory correctly
   ```bash
   docker run -v $(pwd)/config:/data/config arxiv-autosumm
   ```

3. **API key issues**: Use environment variables
   ```bash
   docker run -e OPENAI_API_KEY=your_key arxiv-autosumm
   ```

### Debug Mode
```bash
# Run with shell access
docker run -it --rm \
  -v $(pwd)/config:/data/config \
  arxiv-autosumm:latest shell
```

## Development

### Local development with Docker
```bash
# Mount source code for development
docker run --rm -it \
  -v $(pwd):/app \
  -v $(pwd)/config:/data/config \
  -v $(pwd)/cache:/data/cache \
  -v $(pwd)/output:/data/output \
  arxiv-autosumm:latest shell
```

### Testing changes
```bash
# Build and test locally
docker build -t arxiv-autosumm:dev -f docker/Dockerfile .
docker run --rm arxiv-autosumm:dev test-config
```