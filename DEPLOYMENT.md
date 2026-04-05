# Deployment Guide: SDOH-CKDPred System

This guide provides comprehensive instructions for deploying the CKD Early Detection System in production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Security Configuration](#security-configuration)
3. [Environment Setup](#environment-setup)
4. [SSL/TLS Configuration](#ssltls-configuration)
5. [Database Setup](#database-setup)
6. [Deployment Steps](#deployment-steps)
7. [Health Checks and Monitoring](#health-checks-and-monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Backup and Recovery](#backup-and-recovery)
10. [Scaling Considerations](#scaling-considerations)

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ or RHEL 8+)
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **Memory**: Minimum 8GB RAM (16GB recommended)
- **Storage**: Minimum 50GB available disk space
- **CPU**: 4+ cores recommended

### Software Dependencies

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

## Security Configuration

### 1. Generate Encryption Keys

The system requires several cryptographic keys for security (Requirements 13.1, 13.2):

```bash
# Generate SECRET_KEY for JWT tokens
openssl rand -hex 32

# Generate ENCRYPTION_KEY for data at rest (AES-256)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate strong database password
openssl rand -base64 32

# Generate Redis password
openssl rand -base64 32
```

### 2. Generate DH Parameters for TLS

```bash
# Generate 4096-bit DH parameters (this may take several minutes)
openssl dhparam -out nginx/dhparam.pem 4096
```

### 3. File Permissions

```bash
# Secure sensitive files
chmod 600 .env
chmod 600 nginx/ssl/key.pem
chmod 644 nginx/ssl/cert.pem
chmod 644 nginx/dhparam.pem
```

## Environment Setup

### 1. Create Environment File

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

### 2. Configure Production Variables

Edit `.env` with production values:

```bash
# Application
APP_NAME=SDOH-CKDPred
APP_VERSION=0.1.0
DEBUG=False

# Database - Use strong passwords!
POSTGRES_USER=ckd_prod_user
POSTGRES_PASSWORD=<generated-strong-password>
POSTGRES_DB=ckd_production
POSTGRES_PORT=5432

# Redis - Use strong password!
REDIS_PASSWORD=<generated-strong-password>
REDIS_PORT=6379

# Security - Use generated keys!
SECRET_KEY=<generated-secret-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENCRYPTION_KEY=<generated-encryption-key>

# ML Model
MODEL_PATH=models/sdoh_ckdpred_final.json
MODEL_VERSION=1.0.0

# Risk Thresholds (validated from research)
RISK_THRESHOLD_HIGH=0.65
RISK_THRESHOLD_MODERATE=0.35

# Performance SLAs
PREDICTION_TIMEOUT_MS=500
SHAP_TIMEOUT_MS=200
INTERVENTION_INITIATION_HOURS=1

# Cost-Effectiveness
TARGET_BCR=3.75
COST_STAGE5_PER_YEAR=89000
COST_STAGE3_PER_YEAR=20000

# Fairness Monitoring
MAX_AUROC_DISPARITY=0.05

# CORS - Update with your production domain
CORS_ORIGINS=["https://your-production-domain.com"]

# Ports
HTTP_PORT=80
HTTPS_PORT=443
BACKEND_PORT=8000
```

## SSL/TLS Configuration

### Option 1: Self-Signed Certificates (Development/Testing)

```bash
# Create SSL directory
mkdir -p nginx/ssl

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

### Option 2: Let's Encrypt (Production)

```bash
# Install certbot
sudo apt-get update
sudo apt-get install certbot

# Obtain certificate (replace with your domain)
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates to nginx directory
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem

# Set up auto-renewal
sudo certbot renew --dry-run
```

### Option 3: Commercial Certificate

Place your certificate files in the `nginx/ssl/` directory:
- `cert.pem`: Full certificate chain
- `key.pem`: Private key

### Verify TLS 1.3 Configuration

After deployment, verify TLS 1.3 is enabled:

```bash
# Test TLS version
openssl s_client -connect localhost:443 -tls1_3

# Check with nmap
nmap --script ssl-enum-ciphers -p 443 localhost
```

## Database Setup

### 1. Initialize Database

The database will be automatically initialized on first run. To manually initialize:

```bash
# Start only the database
docker-compose up -d postgres

# Wait for database to be ready
docker-compose exec postgres pg_isready -U ckd_prod_user

# Run migrations (if using Alembic)
docker-compose exec backend alembic upgrade head
```

### 2. Database Encryption at Rest

PostgreSQL data is encrypted at rest using the host filesystem encryption. For additional security:

```bash
# Enable LUKS encryption on the volume mount point
# This should be done before deploying the database
sudo cryptsetup luksFormat /dev/sdX
sudo cryptsetup luksOpen /dev/sdX ckd_encrypted
sudo mkfs.ext4 /dev/mapper/ckd_encrypted
```

## Deployment Steps

### Development Deployment

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### Production Deployment

```bash
# Build and start with production configuration
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Check service status
docker-compose -f docker-compose.prod.yml ps
```

### Verify Deployment

```bash
# Check health endpoints
curl -k https://localhost/health

# Check API documentation
curl -k https://localhost/docs

# Test prediction endpoint (requires authentication)
curl -k -X POST https://localhost/api/v1/predictions/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d @test_patient.json
```

## Health Checks and Monitoring

### Built-in Health Checks

All services include health checks:

```bash
# Check all service health
docker-compose ps

# Individual service health
docker-compose exec backend curl http://localhost:8000/health
docker-compose exec postgres pg_isready -U ckd_prod_user
docker-compose exec redis redis-cli ping
```

### Monitoring Endpoints

- **Backend Health**: `https://your-domain.com/health`
- **API Status**: `https://your-domain.com/`
- **Metrics**: Configure Prometheus/Grafana for production monitoring

### Log Locations

```bash
# Backend logs
docker-compose logs backend

# Nginx logs
docker-compose logs nginx

# PostgreSQL logs
docker-compose logs postgres

# Redis logs
docker-compose logs redis

# Persistent logs
ls -la backend_logs/
```

## Troubleshooting

### Common Issues

#### 1. Services Won't Start

```bash
# Check Docker daemon
sudo systemctl status docker

# Check logs for errors
docker-compose logs

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### 2. Database Connection Errors

```bash
# Verify database is running
docker-compose exec postgres pg_isready

# Check connection from backend
docker-compose exec backend python -c "from app.db.database import engine; print(engine.connect())"

# Check environment variables
docker-compose exec backend env | grep DATABASE
```

#### 3. SSL/TLS Certificate Issues

```bash
# Verify certificate files exist
ls -la nginx/ssl/

# Check certificate validity
openssl x509 -in nginx/ssl/cert.pem -text -noout

# Test TLS connection
openssl s_client -connect localhost:443 -tls1_3
```

#### 4. Performance Issues

```bash
# Check resource usage
docker stats

# Check database performance
docker-compose exec postgres psql -U ckd_prod_user -d ckd_production -c "SELECT * FROM pg_stat_activity;"

# Check slow queries
docker-compose exec postgres psql -U ckd_prod_user -d ckd_production -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

#### 5. Prediction Timeout Errors

```bash
# Check backend logs
docker-compose logs backend | grep -i timeout

# Verify model file exists
docker-compose exec backend ls -la models/

# Test prediction latency
time curl -k -X POST https://localhost/api/v1/predictions/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d @test_patient.json
```

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U ckd_prod_user ckd_production > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated daily backups
cat > /etc/cron.daily/ckd-backup << 'EOF'
#!/bin/bash
BACKUP_DIR=/var/backups/ckd
mkdir -p $BACKUP_DIR
docker-compose exec -T postgres pg_dump -U ckd_prod_user ckd_production | gzip > $BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql.gz
# Keep only last 30 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
EOF
chmod +x /etc/cron.daily/ckd-backup
```

### Database Restore

```bash
# Stop backend to prevent connections
docker-compose stop backend

# Restore from backup
cat backup_20240101_120000.sql | docker-compose exec -T postgres psql -U ckd_prod_user ckd_production

# Restart services
docker-compose start backend
```

### Volume Backup

```bash
# Backup all volumes
docker run --rm \
  -v ckd_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_data_$(date +%Y%m%d).tar.gz /data

docker run --rm \
  -v ckd_redis_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/redis_data_$(date +%Y%m%d).tar.gz /data
```

## Scaling Considerations

### Horizontal Scaling

For high-traffic deployments:

```yaml
# docker-compose.scale.yml
services:
  backend:
    deploy:
      replicas: 4
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

### Load Balancing

Configure Nginx for multiple backend instances:

```nginx
upstream backend_servers {
    least_conn;
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
    server backend4:8000;
}
```

### Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_patient_risk_score ON predictions(patient_id, risk_score);
CREATE INDEX idx_prediction_date ON predictions(prediction_date);
CREATE INDEX idx_risk_tier ON predictions(risk_tier);

-- Analyze tables
ANALYZE predictions;
ANALYZE patients;
```

### Caching Strategy

Redis is configured for caching predictions and SHAP explanations:

```python
# Cache prediction results for 1 hour
CACHE_TTL = 3600

# Cache SHAP explanations for 24 hours
SHAP_CACHE_TTL = 86400
```

## Security Checklist

Before going to production:

- [ ] Change all default passwords
- [ ] Generate strong SECRET_KEY and ENCRYPTION_KEY
- [ ] Configure SSL/TLS certificates
- [ ] Generate DH parameters (4096-bit)
- [ ] Verify TLS 1.3 is enabled
- [ ] Update CORS_ORIGINS with production domain
- [ ] Enable firewall rules (allow only 80, 443)
- [ ] Set up automated backups
- [ ] Configure log rotation
- [ ] Enable monitoring and alerting
- [ ] Review and secure file permissions
- [ ] Disable DEBUG mode
- [ ] Remove development volumes from production compose file
- [ ] Set up intrusion detection (fail2ban)
- [ ] Configure rate limiting in Nginx
- [ ] Enable audit logging
- [ ] Review HIPAA compliance requirements

## Performance Benchmarks

Expected performance metrics:

- **Prediction Latency**: < 500ms (Requirement 2.4)
- **SHAP Explanation**: < 200ms (Requirement 3.5)
- **Intervention Initiation**: < 1 hour (Requirement 5.1)
- **API Throughput**: 100+ requests/second
- **Database Connections**: 100 concurrent connections

## Support and Maintenance

### Regular Maintenance Tasks

```bash
# Weekly: Update Docker images
docker-compose pull
docker-compose up -d

# Monthly: Clean up unused resources
docker system prune -a

# Quarterly: Review and rotate logs
find /var/log/ckd -name "*.log" -mtime +90 -delete

# Quarterly: Update SSL certificates (if using Let's Encrypt)
sudo certbot renew
```

### Monitoring Recommendations

- Set up Prometheus + Grafana for metrics
- Configure alerting for:
  - High prediction latency (> 500ms)
  - Database connection failures
  - High memory/CPU usage
  - SSL certificate expiration
  - Failed health checks

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/security.html)
- [Nginx TLS Configuration](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [HIPAA Compliance Guide](https://www.hhs.gov/hipaa/index.html)

## Contact

For deployment support or questions:
- GitHub Issues: https://github.com/sanjoyp158-sri/sdoh_ckd_pred/issues
- Documentation: See README.md and design documents in `.kiro/specs/`
