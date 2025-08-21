# Distributed WebSocket Deployment Guide

This guide explains how to deploy MEFAPEX ChatBox with distributed WebSocket support for horizontal scaling using Redis pub/sub and multiple workers.

## Overview

The distributed WebSocket system provides:
- **Session Persistence**: WebSocket sessions stored in Redis, survive worker restarts
- **Horizontal Scaling**: Multiple workers can handle WebSocket connections
- **Message Broadcasting**: Pub/sub messaging across workers
- **Automatic Failover**: Sessions automatically cleaned up when workers fail
- **Load Balancing**: Workers can be added/removed dynamically

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │      Redis      │    │   Worker Pool   │
│   (nginx/HAProxy)│    │   (Session +    │    │                 │
│                 │    │    Pub/Sub)     │    │  Worker 1       │
└─────────────────┘    └─────────────────┘    │  Worker 2       │
         │                       │              │  Worker N       │
         │                       │              └─────────────────┘
         │                       │
         └───────────────────────┼─────────────────────────────────┐
                                 │                                 │
                  ┌─────────────────┐                ┌─────────────────┐
                  │  WebSocket      │                │  HTTP API       │
                  │  Connections    │                │  Endpoints      │
                  └─────────────────┘                └─────────────────┘
```

## Prerequisites

1. **Redis Server**: For session storage and pub/sub messaging
2. **Load Balancer**: nginx, HAProxy, or cloud load balancer
3. **ASGI Server**: Uvicorn, Gunicorn+Uvicorn, or Hypercorn

## Configuration

### Environment Variables

```bash
# Redis Configuration (Required for distributed mode)
REDIS_HOST=redis-server
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-redis-password
REDIS_URL=redis://username:password@redis-server:6379/0

# Distributed WebSocket Settings
DISTRIBUTED_WEBSOCKET_ENABLED=true
WEBSOCKET_SESSION_TTL=3600
WORKER_ID=worker-1  # Unique per worker instance
NODE_ID=node-1      # Unique per deployment node

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4  # Number of worker processes
```

### Redis Setup

#### Option 1: Docker Redis
```bash
# Start Redis with Docker
docker run -d \
  --name mefapex-redis \
  -p 6379:6379 \
  -e REDIS_PASSWORD=your-redis-password \
  redis:7-alpine redis-server --requirepass your-redis-password
```

#### Option 2: Redis Cloud/Managed Service
```bash
# Use managed Redis service (AWS ElastiCache, Google Cloud Memorystore, etc.)
REDIS_URL=redis://username:password@your-redis-cluster:6379/0
```

#### Option 3: Redis Cluster (High Availability)
```bash
# For production with high availability
REDIS_URL=redis-cluster://node1:7000,node2:7000,node3:7000
```

## Deployment Options

### Option 1: Uvicorn with Multiple Workers

```bash
# Single command deployment
uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --log-level info
```

### Option 2: Gunicorn with Uvicorn Workers

Create `gunicorn.conf.py`:
```python
# Gunicorn configuration for distributed WebSocket deployment
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', 8000)}"
workers = int(os.getenv('WORKERS', 4))
worker_class = "uvicorn.workers.UvicornWorker"

# Worker configuration
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 120
keepalive = 5

# Process naming
proc_name = "mefapex-chatbox"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Graceful shutdown
graceful_timeout = 30
timeout = 120

# Worker recycling (important for memory management with AI models)
max_requests = 1000
max_requests_jitter = 100

# Enable preload for better memory efficiency with AI models
preload_app = True

# Worker process management
worker_tmp_dir = "/dev/shm"  # Use shared memory for better performance

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("MEFAPEX ChatBox server ready for distributed WebSocket connections")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info(f"Worker {worker.pid} received INT/QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"Worker {worker.pid} about to be forked")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker {worker.pid} spawned")
    
    # Set unique worker ID for distributed WebSocket management
    os.environ['WORKER_ID'] = f"gunicorn-worker-{worker.pid}"

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forked child, re-executing.")

def on_exit(server):
    """Called just before exiting."""
    server.log.info("MEFAPEX ChatBox server shutting down")
```

Run with Gunicorn:
```bash
gunicorn main:app -c gunicorn.conf.py
```

### Option 3: Docker Deployment

Create `Dockerfile.distributed`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash mefapex
RUN chown -R mefapex:mefapex /app
USER mefapex

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run with Gunicorn
CMD ["gunicorn", "main:app", "-c", "gunicorn.conf.py"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  mefapex-worker:
    build:
      context: .
      dockerfile: Dockerfile.distributed
    ports:
      - "8000-8003:8000"  # Scale multiple workers
    environment:
      - REDIS_HOST=redis
      - REDIS_PASSWORD=${REDIS_PASSWORD}
      - DISTRIBUTED_WEBSOCKET_ENABLED=true
      - WORKERS=2
    depends_on:
      redis:
        condition: service_healthy
    deploy:
      replicas: 2  # Run 2 container instances
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - mefapex-worker

volumes:
  redis_data:
```

### Option 4: Kubernetes Deployment

Create `k8s-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mefapex-chatbox
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mefapex-chatbox
  template:
    metadata:
      labels:
        app: mefapex-chatbox
    spec:
      containers:
      - name: mefapex-chatbox
        image: mefapex-chatbox:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_HOST
          value: "redis-service"
        - name: DISTRIBUTED_WEBSOCKET_ENABLED
          value: "true"
        - name: WORKER_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: NODE_ID
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
---
apiVersion: v1
kind: Service
metadata:
  name: mefapex-service
spec:
  selector:
    app: mefapex-chatbox
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

## Load Balancer Configuration

### Nginx Configuration

Create `nginx.conf`:
```nginx
upstream mefapex_backend {
    # Enable session affinity for WebSocket connections
    ip_hash;
    
    server 127.0.0.1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8003 weight=1 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name your-domain.com;

    # WebSocket configuration
    location /ws {
        proxy_pass http://mefapex_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket timeouts
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }

    # Regular HTTP endpoints
    location / {
        proxy_pass http://mefapex_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Add WebSocket health headers to responses
        add_header X-WebSocket-Backend $upstream_addr;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://mefapex_backend/health;
        access_log off;
    }
}
```

### HAProxy Configuration

Create `haproxy.cfg`:
```
global
    daemon
    maxconn 4096

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms
    option httplog

frontend mefapex_frontend
    bind *:80
    default_backend mefapex_backend

backend mefapex_backend
    balance source  # Session affinity for WebSocket
    option httpchk GET /health
    
    server worker1 127.0.0.1:8000 check
    server worker2 127.0.0.1:8001 check
    server worker3 127.0.0.1:8002 check
    server worker4 127.0.0.1:8003 check
```

## Monitoring and Health Checks

### Health Check Endpoint

The application provides comprehensive health checks at `/health`:

```json
{
  "status": "healthy",
  "websocket": {
    "worker_id": "worker-12345",
    "session_store_healthy": true,
    "message_broker_healthy": true,
    "local_connections": 15,
    "total_sessions": 47,
    "total_workers": 3
  },
  "database": {
    "status": "connected",
    "connection_pool": "healthy"
  },
  "redis": {
    "status": "connected",
    "latency_ms": 2.5
  }
}
```

### Monitoring Metrics

The application exposes WebSocket metrics via HTTP headers:
- `X-WebSocket-Local-Connections`: Local connections on this worker
- `X-WebSocket-Worker-ID`: Current worker identifier
- `X-WebSocket-Total-Sessions`: Total sessions across all workers
- `X-WebSocket-Total-Workers`: Number of active workers

### Prometheus Integration

Create `prometheus_metrics.py` for monitoring:
```python
from prometheus_client import Counter, Gauge, Histogram
import time

# WebSocket metrics
websocket_connections = Gauge('websocket_connections_total', 'Total WebSocket connections', ['worker_id'])
websocket_messages = Counter('websocket_messages_total', 'Total WebSocket messages', ['type', 'worker_id'])
websocket_session_duration = Histogram('websocket_session_duration_seconds', 'WebSocket session duration')

# Add to your WebSocket manager:
def update_metrics():
    stats = websocket_manager.get_connection_stats()
    websocket_connections.labels(worker_id=stats['local_stats']['worker_id']).set(
        stats['local_stats']['local_connections']
    )
```

## Scaling Guidelines

### Vertical Scaling
- **CPU**: 2-4 cores per worker for AI model processing
- **Memory**: 4-8GB per worker (AI models are memory-intensive)
- **Redis**: 2-4GB for session storage (depends on session count)

### Horizontal Scaling
1. **Start with 2-4 workers** per server
2. **Monitor CPU and memory usage**
3. **Scale based on WebSocket connection count**
4. **Use sticky sessions** for optimal performance

### Auto-scaling Triggers
```yaml
# Kubernetes HPA example
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mefapex-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mefapex-chatbox
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: websocket_connections_per_pod
      target:
        type: AverageValue
        averageValue: "50"
```

## Troubleshooting

### Common Issues

1. **Sessions not persisting**: Check Redis connectivity and configuration
2. **Messages not broadcasting**: Verify Redis pub/sub channels are working
3. **Worker conflicts**: Ensure unique WORKER_ID for each worker process
4. **Memory leaks**: Monitor AI model memory usage and enable cleanup

### Debug Commands

```bash
# Check Redis connectivity
redis-cli -h redis-server -p 6379 ping

# Monitor Redis pub/sub
redis-cli -h redis-server -p 6379 MONITOR

# Check WebSocket sessions in Redis
redis-cli -h redis-server -p 6379 KEYS "ws_session:*"

# View worker health
curl http://localhost:8000/health | jq

# Monitor WebSocket connections
curl -I http://localhost:8000/ | grep X-WebSocket
```

### Log Analysis

```bash
# Filter WebSocket-related logs
grep "WebSocket\|websocket" /var/log/mefapex/app.log

# Monitor worker communication
grep "broadcast\|pub/sub" /var/log/mefapex/app.log

# Check session cleanup
grep "cleanup\|expired" /var/log/mefapex/app.log
```

## Security Considerations

1. **Redis Security**: Use authentication and TLS for Redis connections
2. **WebSocket Authentication**: Validate JWT tokens for WebSocket connections
3. **Network Security**: Use VPN or private networks for worker communication
4. **Rate Limiting**: Implement per-user connection limits
5. **Message Validation**: Sanitize all WebSocket messages

## Performance Optimization

1. **Redis Optimization**: Use Redis clustering for high availability
2. **Connection Pooling**: Configure appropriate connection pool sizes
3. **Memory Management**: Monitor and tune AI model memory usage
4. **Load Balancing**: Use consistent hashing for better distribution
5. **Caching**: Implement message caching for frequently accessed data

## Migration from Single Worker

To migrate from single-worker deployment:

1. **Setup Redis** server
2. **Update configuration** to enable distributed mode
3. **Test with single worker** first
4. **Gradually add more workers**
5. **Update load balancer** configuration
6. **Monitor session persistence**

The system automatically falls back to in-memory mode if Redis is unavailable, ensuring zero-downtime migration.
