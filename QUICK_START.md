# Quick Start Guide

This guide provides quick commands for common operations with the CKD Early Detection System.

## Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/sanjoyp158-sri/sdoh_ckd_pred.git
cd sdoh_ckd_pred

# 2. Run setup script (generates keys, creates .env)
./scripts/setup-production.sh

# 3. Generate SSL certificates
./scripts/generate-ssl-certs.sh

# 4. Place your ML model
cp /path/to/model.json models/sdoh_ckdpred_final.json
```

## Development Mode

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

## Production Mode

```bash
# Start with production configuration
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down

# Restart a specific service
docker-compose -f docker-compose.prod.yml restart backend
```

## Health Checks

```bash
# Check all services
docker-compose ps

# Test health endpoint
curl -k https://localhost/health

# Test API root
curl -k https://localhost/

# Check backend directly
curl http://localhost:8000/health
```

## Database Operations

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U ckd_user -d ckd_db

# Run migrations
docker-compose exec backend alembic upgrade head

# Create backup
docker-compose exec postgres pg_dump -U ckd_user ckd_db > backup.sql

# Restore backup
cat backup.sql | docker-compose exec -T postgres psql -U ckd_user ckd_db
```

## Redis Operations

```bash
# Access Redis CLI
docker-compose exec redis redis-cli

# Check Redis info
docker-compose exec redis redis-cli INFO

# Clear cache
docker-compose exec redis redis-cli FLUSHALL
```

## Logs and Debugging

```bash
# View all logs
docker-compose logs

# Follow specific service logs
docker-compose logs -f backend
docker-compose logs -f nginx
docker-compose logs -f postgres

# View last 100 lines
docker-compose logs --tail=100 backend

# Check container resource usage
docker stats
```

## Testing

```bash
# Run backend tests
docker-compose exec backend pytest

# Run with coverage
docker-compose exec backend pytest --cov=app

# Run property-based tests
docker-compose exec backend pytest tests/property/ -v

# Run specific test file
docker-compose exec backend pytest tests/unit/test_xgboost_classifier.py
```

## API Testing

```bash
# Get API documentation
curl -k https://localhost/docs

# Test prediction endpoint (requires auth)
curl -k -X POST https://localhost/api/v1/predictions/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "patient_id": "test-001",
    "clinical": {
      "egfr": 45.0,
      "uacr": 150.0,
      "hba1c": 7.5,
      "systolic_bp": 140,
      "diastolic_bp": 90,
      "bmi": 28.5
    },
    "administrative": {
      "visit_frequency_12mo": 8,
      "insurance_type": "Medicare"
    },
    "sdoh": {
      "adi_percentile": 75,
      "food_desert": true,
      "housing_stability_score": 0.6,
      "transportation_access_score": 0.4
    }
  }'
```

## SSL/TLS Verification

```bash
# Test TLS 1.3 connection
openssl s_client -connect localhost:443 -tls1_3

# Check certificate details
openssl x509 -in nginx/ssl/cert.pem -text -noout

# Verify certificate and key match
openssl x509 -noout -modulus -in nginx/ssl/cert.pem | openssl md5
openssl rsa -noout -modulus -in nginx/ssl/key.pem | openssl md5

# Test with curl (verbose)
curl -vI https://localhost/health
```

## Maintenance

```bash
# Update Docker images
docker-compose pull
docker-compose up -d

# Clean up unused resources
docker system prune -a

# View disk usage
docker system df

# Restart all services
docker-compose restart

# Stop and remove all containers, networks, volumes
docker-compose down -v
```

## Environment Variables

```bash
# View environment variables in container
docker-compose exec backend env

# Update environment variable
# 1. Edit .env file
# 2. Restart services
docker-compose up -d --force-recreate
```

## Troubleshooting

```bash
# Service won't start
docker-compose logs <service-name>
docker-compose ps
docker-compose down && docker-compose up -d

# Database connection issues
docker-compose exec postgres pg_isready -U ckd_user
docker-compose exec backend python -c "from app.db.database import engine; print(engine.connect())"

# Permission issues
sudo chown -R $USER:$USER .
chmod 600 .env
chmod 600 nginx/ssl/key.pem

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

## Performance Monitoring

```bash
# Check resource usage
docker stats

# Check database performance
docker-compose exec postgres psql -U ckd_user -d ckd_db -c "SELECT * FROM pg_stat_activity;"

# Check slow queries
docker-compose exec postgres psql -U ckd_user -d ckd_db -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Monitor prediction latency
time curl -k -X POST https://localhost/api/v1/predictions/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d @test_patient.json
```

## Security

```bash
# Generate new SECRET_KEY
openssl rand -hex 32

# Generate new ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Check file permissions
ls -la .env
ls -la nginx/ssl/

# Scan for vulnerabilities (if trivy installed)
trivy image ckd-backend-test
```

## Backup and Restore

```bash
# Full backup
./scripts/backup.sh

# Database backup
docker-compose exec postgres pg_dump -U ckd_user ckd_db | gzip > backup_$(date +%Y%m%d).sql.gz

# Volume backup
docker run --rm -v ckd_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_data.tar.gz /data

# Restore database
gunzip < backup_20240101.sql.gz | docker-compose exec -T postgres psql -U ckd_user ckd_db
```

## Useful Aliases

Add these to your `~/.bashrc` or `~/.zshrc`:

```bash
# Docker Compose shortcuts
alias dc='docker-compose'
alias dcp='docker-compose -f docker-compose.prod.yml'
alias dcl='docker-compose logs -f'
alias dce='docker-compose exec'
alias dcr='docker-compose restart'

# CKD-specific
alias ckd-start='docker-compose up -d'
alias ckd-stop='docker-compose down'
alias ckd-logs='docker-compose logs -f backend'
alias ckd-test='docker-compose exec backend pytest'
alias ckd-health='curl -k https://localhost/health'
```

## Next Steps

- Review [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive deployment guide
- Check [README.md](README.md) for architecture and features
- See [API Documentation](https://localhost/docs) for endpoint details
- Review security checklist in DEPLOYMENT.md before production deployment
