# Deployment Guide

## Quick Start (Local Development)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables
```bash
# Create .env file
echo "GOOGLE_API_KEY=your_key_here" > .env
echo "DATABASE_URL=sqlite:///./leadfinder.db" >> .env
```

### 3. Initialize Database
```bash
python -c "from app.core.database import init_db; init_db()"
```

### 4. Run Server
```bash
uvicorn app.main:app --reload
```

### 5. Test with Example Script
```bash
python example_usage.py
```

## Production Deployment

### Option 1: Docker (Recommended)

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - DATABASE_URL=postgresql://postgres:password@db:5432/leadfinder
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=leadfinder
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Deploy:
```bash
docker-compose up -d
```

### Option 2: Cloud Platforms

#### **AWS (Elastic Beanstalk)**
```bash
eb init -p python-3.11 leadfinder-ai
eb create leadfinder-prod
eb deploy
```

#### **Google Cloud (Cloud Run)**
```bash
gcloud run deploy leadfinder-ai \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### **Azure (App Service)**
```bash
az webapp up --name leadfinder-ai \
  --runtime "PYTHON:3.11" \
  --sku B1
```

### Option 3: VPS (DigitalOcean, Linode, etc.)

```bash
# On server
git clone <your-repo>
cd DeepLeads

# Setup Python environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup environment
cp .env.example .env
nano .env  # Add your keys

# Setup systemd service
sudo nano /etc/systemd/system/leadfinder.service
```

`/etc/systemd/system/leadfinder.service`:
```ini
[Unit]
Description=DeepLeads AI API
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/leadfinder
Environment="PATH=/var/www/leadfinder/venv/bin"
ExecStart=/var/www/leadfinder/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl start leadfinder
sudo systemctl enable leadfinder
```

## Database Setup

### PostgreSQL (Recommended for Production)

```bash
# Install PostgreSQL
sudo apt-get install postgresql

# Create database
sudo -u postgres createdb leadfinder

# Update .env
DATABASE_URL=postgresql://user:password@localhost:5432/leadfinder
```

### Initialize tables
```bash
python -c "from app.core.database import init_db; init_db()"
```

## Environment Variables

Required:
- `GOOGLE_API_KEY` - Your Gemini API key
- `DATABASE_URL` - Database connection string

Optional:
- `SENDGRID_API_KEY` - For email sending
- `SMTP_*` - SMTP configuration
- `PERPLEXITY_API_KEY` - Alternative AI provider

## Monitoring & Logging

Logs are written to:
- Console (stdout)
- `logs/leadfinder.log` (file)

For production monitoring, integrate:
- Sentry for error tracking
- DataDog/New Relic for APM
- Prometheus for metrics

## Security Checklist

- [ ] Change default SECRET_KEY
- [ ] Use environment variables (never commit .env)
- [ ] Enable HTTPS (SSL/TLS)
- [ ] Set up firewall rules
- [ ] Use strong database passwords
- [ ] Implement rate limiting
- [ ] Enable CORS only for trusted domains
- [ ] Regular security updates
- [ ] Backup database regularly

## Performance Optimization

1. **Database Indexing** - Already included in models
2. **Caching** - Add Redis for API responses
3. **Rate Limiting** - Implement per-user limits
4. **Background Tasks** - Use Celery for long operations
5. **CDN** - If serving static assets

## Scaling

For high volume (>1000 leads/day):

1. **Horizontal Scaling**
   - Deploy multiple API instances
   - Use load balancer (nginx, ALB)
   - Shared database

2. **Queue System**
   - Celery + Redis for background tasks
   - Separate workers for discovery/enrichment

3. **Database**
   - PostgreSQL with connection pooling
   - Read replicas for queries
   - Regular optimization

4. **Caching**
   - Redis for frequent queries
   - Cache enrichment data (24hr TTL)

