# SlideGenie Test Infrastructure

This directory contains the comprehensive test infrastructure for SlideGenie, including test factories, fixtures, CI/CD configurations, and coverage reporting.

## Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Data Factories](#test-data-factories)
- [Fixtures](#fixtures)
- [CI/CD Integration](#cicd-integration)
- [Coverage Reporting](#coverage-reporting)
- [Best Practices](#best-practices)

## Overview

SlideGenie's test infrastructure provides:

- **Factory Boy** factories for generating test data
- **Academic content fixtures** for realistic testing
- **Multi-environment CI/CD** support (GitHub Actions, GitLab CI, Jenkins)
- **Comprehensive coverage reporting** with enforcement
- **Docker-based test environment** for consistency
- **Performance and security testing** integration

## Test Structure

```
tests/
├── unit/               # Unit tests for individual components
├── integration/        # Integration tests with real services
├── e2e/               # End-to-end API tests
├── performance/       # Performance and load tests
├── security/          # Security-focused tests
├── ai_quality/        # AI output quality tests
├── factories/         # Test data factories
├── fixtures/          # Static test data and files
├── mocks/            # Mock objects and services
└── scripts/          # Test environment setup scripts
```

## Running Tests

### Quick Start

```bash
# Set up test environment
./tests/scripts/setup_test_env.sh

# Run all tests
poetry run pytest

# Run specific test suites
poetry run pytest tests/unit          # Unit tests only
poetry run pytest tests/integration   # Integration tests
poetry run pytest tests/e2e           # End-to-end tests

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run in parallel
poetry run pytest -n auto
```

### Docker-based Testing

```bash
# Start test services
docker-compose -f tests/docker-compose.test.yml up -d

# Run tests in Docker
docker-compose -f tests/docker-compose.test.yml run test-runner

# Run performance tests
docker-compose -f tests/docker-compose.test.yml --profile performance up

# Clean up
docker-compose -f tests/docker-compose.test.yml down -v
```

## Test Data Factories

We use Factory Boy to generate test data dynamically:

### User Factory

```python
from tests.factories import UserFactory

# Create a basic user
user = UserFactory()

# Create specific user types
admin = UserFactory(admin=True)
professor = UserFactory(professor=True)
student = UserFactory(student=True)
free_user = UserFactory(free_user=True)
```

### Presentation Factory

```python
from tests.factories import PresentationFactory, SlideFactory

# Create a conference presentation
presentation = PresentationFactory(conference_presentation=True)

# Create with specific slides
presentation = PresentationFactory()
slides = [SlideFactory(presentation_id=presentation['id']) for _ in range(10)]
```

### Academic Content Factory

```python
from tests.factories import ResearchPaperFactory, ThesisFactory, CitationFactory

# Create research paper
paper = ResearchPaperFactory()

# Create thesis
thesis = ThesisFactory(thesis_type="phd")

# Create citations
citations = [CitationFactory(recent=True) for _ in range(5)]
```

### File Factory

```python
from tests.factories import FileFactory, MockFileFactory

# Create file metadata
pdf_file = FileFactory(pdf_research_paper=True)

# Create mock file for upload testing
mock_file = MockFileFactory(content_type="pdf")
```

## Fixtures

### Academic Content Fixtures

Located in `tests/fixtures/academic_content.py`:

```python
@pytest.fixture
def research_paper_content():
    """Sample research paper content."""
    return {...}

@pytest.fixture
def conference_presentation():
    """Conference presentation example."""
    return {...}

@pytest.fixture
def math_formulas():
    """LaTeX mathematical formulas."""
    return {...}
```

### Using Fixtures

```python
def test_presentation_generation(research_paper_content):
    # Use the fixture data
    result = generate_presentation(research_paper_content)
    assert result.slide_count > 10
```

### Sample Files

Pre-generated sample files are available in `tests/fixtures/files/`:
- PDF documents
- LaTeX files
- Bibliography files
- Academic papers

## CI/CD Integration

### GitHub Actions

Configuration: `.github/workflows/test.yml`

Features:
- Matrix testing across Python versions
- Parallel job execution
- Coverage upload to Codecov
- Security scanning with Trivy
- Performance test scheduling

### GitLab CI

Configuration: `.gitlab-ci.yml`

Features:
- Docker-in-Docker support
- SonarQube integration
- Staged deployment
- Nightly regression tests

### Jenkins

Configuration: `Jenkinsfile`

Features:
- Pipeline as Code
- Quality gates
- Blue-Green deployments
- Slack notifications

## Coverage Reporting

### Configuration

Coverage settings in `.coveragerc`:

```ini
[run]
source = app
branch = True
parallel = True
omit = */tests/*, */migrations/*

[report]
fail_under = 80
precision = 2
show_missing = True
```

### Viewing Coverage

```bash
# Generate HTML report
poetry run pytest --cov=app --cov-report=html

# Open report
open htmlcov/index.html

# Check coverage threshold
poetry run coverage report --fail-under=80
```

### Coverage Enforcement

- **Unit tests**: Minimum 80% coverage
- **Integration tests**: Focus on critical paths
- **Excluded**: Migrations, config files, type stubs

## Best Practices

### 1. Test Organization

```python
# Good: Descriptive test names
def test_user_can_create_presentation_from_pdf():
    ...

# Good: Arrange-Act-Assert pattern
def test_slide_generation():
    # Arrange
    user = UserFactory()
    document = FileFactory(pdf_research_paper=True)
    
    # Act
    result = generate_slides(user, document)
    
    # Assert
    assert result.success
    assert len(result.slides) > 0
```

### 2. Factory Usage

```python
# Good: Use traits for specific scenarios
thesis_defense = PresentationFactory(thesis_defense=True)

# Good: Override specific attributes
custom_user = UserFactory(
    email="test@university.edu",
    institution="MIT"
)
```

### 3. Fixture Management

```python
# Good: Scoped fixtures for efficiency
@pytest.fixture(scope="session")
def database():
    # Setup database once per session
    return setup_test_db()

# Good: Cleanup in fixtures
@pytest.fixture
def temp_file():
    file = create_temp_file()
    yield file
    file.unlink()  # Cleanup
```

### 4. Async Testing

```python
# Good: Use pytest-asyncio
@pytest.mark.asyncio
async def test_websocket_connection():
    async with websocket_connect("/ws") as ws:
        await ws.send_json({"type": "ping"})
        response = await ws.receive_json()
        assert response["type"] == "pong"
```

### 5. Performance Testing

```python
# Good: Benchmark critical operations
@pytest.mark.benchmark
def test_pdf_processing_performance(benchmark):
    pdf_file = FileFactory(pdf_research_paper=True)
    result = benchmark(process_pdf, pdf_file)
    assert result.processing_time < 5.0  # seconds
```

## Environment Variables

Test-specific environment variables in `.env.test`:

```bash
# Database
DATABASE_URL=postgresql://slidegenie_test:testpass123@localhost:5433/slidegenie_test

# Services
REDIS_URL=redis://localhost:6380
MINIO_ENDPOINT=localhost:9001

# Testing
TESTING=true
TEST_DATABASE_RESET=true
COVERAGE_THRESHOLD=80
```

## Troubleshooting

### Common Issues

1. **Database connection failed**
   ```bash
   # Check if test database is running
   docker ps | grep postgres-test
   
   # Restart test services
   docker-compose -f tests/docker-compose.test.yml restart
   ```

2. **Fixtures not found**
   ```bash
   # Regenerate fixtures
   poetry run python tests/scripts/generate_fixtures.py
   ```

3. **Coverage below threshold**
   ```bash
   # Find uncovered lines
   poetry run coverage report -m
   
   # Generate detailed HTML report
   poetry run coverage html
   ```

## Contributing

When adding new tests:

1. Use appropriate factories for test data
2. Add fixtures for reusable test scenarios
3. Ensure tests are deterministic and isolated
4. Update CI/CD configurations if needed
5. Maintain coverage above 80%

For more information, see the main project documentation.