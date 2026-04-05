# Nginx Configuration

This directory contains the Nginx reverse proxy configuration for the CKD Early Detection System.

## Files

- `nginx.conf` - Main Nginx configuration with TLS 1.3 support
- `ssl/` - Directory for SSL/TLS certificates (not tracked in git)
- `dhparam.pem` - Diffie-Hellman parameters for Perfect Forward Secrecy (not tracked in git)

## SSL Certificate Setup

### Option 1: Generate Self-Signed Certificates (Development)

```bash
# Run the SSL generation script from project root
./scripts/generate-ssl-certs.sh
```

Or manually:

```bash
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
  -keyout ssl/key.pem \
  -out ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

### Option 2: Let's Encrypt (Production)

```bash
# Install certbot
sudo apt-get install certbot

# Obtain certificate
sudo certbot certonly --standalone -d your-domain.com

# Copy to nginx directory
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem
```

### Option 3: Commercial Certificate

Place your certificate files in the `ssl/` directory:
- `cert.pem` - Full certificate chain
- `key.pem` - Private key

## Generate DH Parameters

For Perfect Forward Secrecy, generate DH parameters:

```bash
# From project root
openssl dhparam -out nginx/dhparam.pem 4096
```

This will take several minutes but only needs to be done once.

## TLS 1.3 Configuration

The nginx.conf is configured to use TLS 1.3 only (Requirement 13.2):

- **Protocol**: TLS 1.3 only (no fallback)
- **Cipher Suites**: 
  - TLS_AES_128_GCM_SHA256
  - TLS_AES_256_GCM_SHA384
  - TLS_CHACHA20_POLY1305_SHA256
- **Features**:
  - HSTS with preload
  - OCSP stapling
  - Perfect Forward Secrecy
  - Session resumption disabled

## Verify TLS Configuration

After deployment, verify TLS 1.3 is working:

```bash
# Test TLS 1.3 connection
openssl s_client -connect localhost:443 -tls1_3

# Check cipher suites
nmap --script ssl-enum-ciphers -p 443 localhost

# Test with curl
curl -vI https://localhost/health
```

## Security Headers

The configuration includes security headers:
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security (HSTS)
- Content-Security-Policy

## File Permissions

Ensure proper permissions:

```bash
chmod 644 nginx.conf
chmod 644 ssl/cert.pem
chmod 600 ssl/key.pem
chmod 644 dhparam.pem
```

## Troubleshooting

### Certificate Errors

```bash
# Verify certificate
openssl x509 -in ssl/cert.pem -text -noout

# Check certificate and key match
openssl x509 -noout -modulus -in ssl/cert.pem | openssl md5
openssl rsa -noout -modulus -in ssl/key.pem | openssl md5
```

### Nginx Configuration Test

```bash
# Test configuration
docker-compose exec nginx nginx -t

# Reload configuration
docker-compose exec nginx nginx -s reload
```

### View Nginx Logs

```bash
# Access logs
docker-compose logs nginx

# Follow logs
docker-compose logs -f nginx
```

## References

- [Nginx TLS Configuration](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [TLS 1.3 Specification](https://tools.ietf.org/html/rfc8446)
