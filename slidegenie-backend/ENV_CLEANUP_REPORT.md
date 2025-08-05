# Environment Variables Cleanup Report

## 🗑️ Variables You Can REMOVE from .env

### 1. **MinIO/Storage Variables** (NOT IMPLEMENTED)
```bash
MINIO_ENDPOINT=localhost:9000        # ❌ Remove
MINIO_ACCESS_KEY=minioadmin          # ❌ Remove
MINIO_SECRET_KEY=minioadmin          # ❌ Remove
MINIO_BUCKET_NAME=slidegenie         # ❌ Remove
MINIO_USE_SSL=false                  # ❌ Remove
MINIO_REGION=us-east-1               # ❌ Remove
```
**Why**: The S3Manager class exists but has NO actual implementation. It just has placeholder methods.

### 2. **Redis Variables** (NOT USED)
```bash
REDIS_HOST=localhost                 # ❌ Remove
REDIS_PORT=6379                      # ❌ Remove
REDIS_PASSWORD=                      # ❌ Remove
REDIS_DB=0                           # ❌ Remove
REDIS_URL=redis://...                # ❌ Remove
```
**Why**: RedisCache class exists but is NEVER imported or used anywhere in the codebase.

### 3. **Celery Variables** (NOT USED)
```bash
CELERY_BROKER_URL=redis://...        # ❌ Remove
CELERY_RESULT_BACKEND=redis://...    # ❌ Remove
```
**Why**: The code uses ARQ for task queues, not Celery. Celery is imported but never configured.

### 4. **Export Settings** (NOT REFERENCED)
```bash
EXPORT_TIMEOUT_SECONDS=300           # ❌ Remove
MAX_CONCURRENT_EXPORTS=5             # ❌ Remove
```
**Why**: Defined in .env but never accessed in code.

### 5. **Monitoring** (NOT PROPERLY USED)
```bash
PROMETHEUS_ENABLED=false             # ❌ Remove
METRICS_PORT=9090                    # ❌ Remove
```
**Why**: Metrics are always collected regardless of PROMETHEUS_ENABLED. METRICS_PORT is never used.

### 6. **Rate Limiting** (HARDCODED)
```bash
RATE_LIMIT_REQUESTS=100              # ❌ Remove
RATE_LIMIT_PERIOD=60                 # ❌ Remove
```
**Why**: rate_limiter.py uses hardcoded values (100 requests per minute), ignoring these settings.

## ✅ Variables You MUST KEEP

### Essential for MVP:
1. **App Settings**: APP_NAME, DEBUG, LOG_LEVEL
2. **API Settings**: API_V1_PREFIX, BACKEND_CORS_ORIGINS
3. **Security**: SECRET_KEY, ALGORITHM, ACCESS_TOKEN_*
4. **Database**: DATABASE_URL (for Supabase)
5. **AI Keys**: OPENAI_API_KEY, ANTHROPIC_API_KEY
6. **File Upload**: MAX_UPLOAD_SIZE_MB, ALLOWED_UPLOAD_EXTENSIONS

### Optional but Useful:
1. **OAuth**: GOOGLE_CLIENT_ID/SECRET (if using Google login)
2. **Email**: SMTP_* settings (if sending emails)
3. **Error Tracking**: SENTRY_DSN (if using Sentry)

## 🚨 Code Issues Found

1. **Fake Storage Implementation**: The S3Manager has methods that just pass or return mock data
2. **Unused Redis**: Infrastructure exists but no actual usage
3. **Config Mismatch**: Many env vars defined in config.py but never used
4. **Hardcoded Values**: Rate limiting ignores env settings

## 💡 For Supabase Migration

Since MinIO/S3 isn't actually implemented, you'll need to:
1. Either implement the S3Manager methods properly for Supabase Storage
2. Or remove file storage features until actually needed

The current code won't actually store files anywhere despite having the infrastructure!