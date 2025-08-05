# SlideGenie Integration Tests

This directory contains comprehensive integration tests for the SlideGenie API, covering all major functionality including presentation generation, file uploads, exports, authentication, and real-time features.

## Test Structure

```
tests/integration/
├── api/                    # API endpoint integration tests
│   ├── test_presentation_flow.py    # Full presentation generation flow
│   ├── test_crud_operations.py      # CRUD operations with DB verification
│   └── test_realtime_websocket.py   # WebSocket and real-time features
├── auth/                   # Authentication integration tests
│   ├── test_auth_flows.py           # Registration, login, OAuth, password reset
│   └── test_rbac_and_api_keys.py   # RBAC and API key authentication
├── file_upload/            # File upload integration tests
│   └── test_file_upload_flow.py     # PDF, DOCX, LaTeX upload and processing
├── export/                 # Export functionality tests
│   └── test_export_flow.py          # PPTX, PDF, LaTeX export with queue
├── conftest.py             # Shared fixtures and test configuration
├── docker-compose.test.yml # Docker environment for integration tests
└── README.md              # This file
```

## Running Integration Tests

### Using Docker Compose (Recommended)

```bash
# Run all integration tests
docker-compose -f tests/integration/docker-compose.test.yml up --abort-on-container-exit

# Run with coverage report
docker-compose -f tests/integration/docker-compose.test.yml up test-runner

# View coverage report (after tests complete)
docker-compose -f tests/integration/docker-compose.test.yml --profile reports up -d test-report-server
# Open http://localhost:8080 in browser
```

### Using pytest directly

```bash
# Ensure test containers are running
docker-compose -f tests/integration/docker-compose.test.yml up -d test-postgres test-redis test-minio test-clamav

# Run integration tests
pytest tests/integration -v -m integration

# Run specific test category
pytest tests/integration/api -v
pytest tests/integration/auth -v
pytest tests/integration/file_upload -v
pytest tests/integration/export -v

# Run with coverage
pytest tests/integration -v --cov=app --cov-report=html
```

### Using Make

```bash
# Run all integration tests
make test-integration

# Run with coverage
make test-integration-coverage
```

## Test Categories

### 1. API Endpoint Tests (`api/`)

#### Presentation Generation Flow
- Full generation workflow from request to completion
- Template-based generation
- Progress tracking
- Concurrent requests handling
- Failure scenarios and recovery
- Citation integration

#### CRUD Operations
- Create, read, update, delete presentations
- Permission checking
- Pagination and search
- Bulk operations
- Presentation duplication

#### Real-time WebSocket
- WebSocket authentication
- Real-time presentation updates
- Collaborative editing with locks
- Presence tracking
- Cursor synchronization
- Reconnection handling

### 2. Authentication Tests (`auth/`)

#### Authentication Flows
- User registration with email verification
- Login with session management
- OAuth (Google, Microsoft) authentication
- Password reset flow
- Account lockout and rate limiting

#### RBAC and API Keys
- Role-based endpoint access
- Permission enforcement
- API key lifecycle
- Scope-based restrictions
- Usage tracking and rate limiting

### 3. File Upload Tests (`file_upload/`)

- PDF upload and processing
- DOCX file handling
- LaTeX compilation
- Large file handling
- Virus scanning integration
- File metadata extraction
- Concurrent uploads
- Input validation and sanitization

### 4. Export Tests (`export/`)

- PPTX generation
- PDF export with options
- LaTeX Beamer export
- Queue processing
- Download link management
- Batch exports
- Format validation

## Test Fixtures

### Database Fixtures
- `db_session`: Async database session
- `test_user`: Pre-created test user
- `admin_user`: Admin user for permission tests
- `cleanup_database`: Database cleanup after tests

### Authentication Fixtures
- `authenticated_client`: HTTP client with auth headers
- `admin_client`: Admin authenticated client
- `auth_tokens`: Valid JWT tokens
- `test_api_key`: API key for testing

### File Fixtures
- `sample_pdf_file`: Test PDF file
- `sample_docx_file`: Test DOCX file
- `sample_latex_file`: Test LaTeX file
- `large_file`: File exceeding size limits
- `malicious_file`: File with virus signature

### Mock Fixtures
- `mock_ai_responses`: Mock AI service responses
- `mock_email_service`: Mock email sending
- `mock_oauth_providers`: Mock OAuth providers

## Environment Variables

The integration tests use the following environment variables:

```bash
# Database
POSTGRES_HOST=test-postgres
POSTGRES_USER=test_user
POSTGRES_PASSWORD=test_password
POSTGRES_DB=slidegenie_test

# Redis
REDIS_HOST=test-redis
REDIS_PORT=6379

# MinIO
MINIO_ENDPOINT=test-minio:9000
MINIO_ACCESS_KEY=test_access_key
MINIO_SECRET_KEY=test_secret_key

# Testing flags
TESTING=true
ENVIRONMENT=test
```

## Writing New Integration Tests

### Test Structure Template

```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestFeatureName:
    """Test description."""
    
    async def test_happy_path(self, authenticated_client, db_session):
        """Test successful scenario."""
        # Arrange
        test_data = {...}
        
        # Act
        response = await authenticated_client.post("/api/v1/endpoint", json=test_data)
        
        # Assert
        assert response.status_code == 200
        
        # Verify database state
        result = await db_session.execute(...)
        assert result is not None
    
    async def test_error_handling(self, authenticated_client):
        """Test error scenarios."""
        # Test various error conditions
        pass
```

### Best Practices

1. **Use Markers**: Always mark integration tests with `@pytest.mark.integration`
2. **Clean State**: Each test should start with a clean state
3. **Database Verification**: Verify both API responses and database state
4. **Async/Await**: Use async functions for all database operations
5. **Realistic Data**: Use realistic test data that matches production scenarios
6. **Error Testing**: Test both success and failure paths
7. **Timeouts**: Set appropriate timeouts for long-running operations

## Continuous Integration

The integration tests are configured to run in CI/CD pipelines:

```yaml
# .github/workflows/integration-tests.yml
- name: Run Integration Tests
  run: |
    docker-compose -f tests/integration/docker-compose.test.yml up \
      --abort-on-container-exit \
      --exit-code-from test-runner
```

## Troubleshooting

### Common Issues

1. **Container startup failures**
   ```bash
   # Check container logs
   docker-compose -f tests/integration/docker-compose.test.yml logs test-postgres
   ```

2. **Database connection errors**
   ```bash
   # Ensure containers are healthy
   docker-compose -f tests/integration/docker-compose.test.yml ps
   ```

3. **Test timeouts**
   - Increase timeout values in test configuration
   - Check for blocking operations

4. **Flaky tests**
   - Add proper wait conditions
   - Use explicit waits instead of sleep
   - Ensure proper test isolation

## Performance Considerations

- Tests use testcontainers for isolation
- Database is rolled back after each test
- Parallel test execution is supported
- Use `pytest-xdist` for parallel runs:
  ```bash
  pytest tests/integration -n auto
  ```

## Coverage Goals

- Minimum 80% code coverage for critical paths
- 100% coverage for authentication flows
- Full coverage of error handling paths
- Integration points with external services