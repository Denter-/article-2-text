# Testing Guide

**Comprehensive testing procedures for the Article Extraction System**

---

## 🎯 Testing Strategy

### **Testing Levels**
1. **Unit Tests** - Test individual functions and methods
2. **Integration Tests** - Test component interactions
3. **End-to-End Tests** - Test complete workflows
4. **Performance Tests** - Test system performance
5. **Quality Tests** - Test extraction quality

---

## 🧪 Unit Testing

### **Python Unit Tests**
```bash
# Run all Python tests
python -m pytest tests/python/

# Run specific test file
python -m pytest tests/python/test_extraction.py

# Run with coverage
python -m pytest --cov=src tests/python/
```

### **Go Unit Tests**
```bash
# Run API tests
cd api && go test ./...

# Run worker tests
cd worker-go && go test ./...

# Run with coverage
cd api && go test -cover ./...
```

### **Frontend Unit Tests**
```bash
# Run React tests
cd frontend && npm test

# Run with coverage
cd frontend && npm run test:coverage
```

---

## 🔗 Integration Testing

### **API Integration Tests**
```bash
# Test API endpoints
./test_api.sh

# Test authentication
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Test extraction workflow
curl -X POST http://localhost:8080/api/v1/extract/single \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/article"}'
```

### **Database Integration Tests**
```bash
# Test database connections
psql -U article_user -d article_extraction -c "SELECT 1;"

# Test migrations
for migration in shared/db/migrations/*.sql; do
    psql -U article_user -d article_extraction -f "$migration"
done

# Test data operations
python tests/integration/test_database.py
```

### **Redis Integration Tests**
```bash
# Test Redis connection
redis-cli ping

# Test job queue
python tests/integration/test_queue.py
```

---

## 🎯 End-to-End Testing

### **Complete Workflow Test**
```bash
# Test full extraction workflow
./test_e2e.sh

# Test Python CLI workflow
python src/article_extractor.py https://example.com/article

# Test API workflow
python tests/e2e/test_api_workflow.py

# Test frontend workflow
cd frontend && npm run test:e2e
```

### **Cross-Platform Testing**
```bash
# Test on different operating systems
docker run --rm -v $(pwd):/app -w /app python:3.9 python src/article_extractor.py --help

# Test with different Python versions
python3.8 src/article_extractor.py --help
python3.9 src/article_extractor.py --help
python3.10 src/article_extractor.py --help
```

---

## 📊 Performance Testing

### **Load Testing**
```bash
# Test API performance
ab -n 1000 -c 10 http://localhost:8080/health

# Test extraction performance
python tests/performance/test_extraction_speed.py

# Test database performance
python tests/performance/test_database_performance.py
```

### **Memory Testing**
```bash
# Test memory usage
python tests/performance/test_memory_usage.py

# Test memory leaks
python tests/performance/test_memory_leaks.py
```

### **Concurrency Testing**
```bash
# Test concurrent extractions
python tests/performance/test_concurrent_extraction.py

# Test worker performance
python tests/performance/test_worker_performance.py
```

---

## 🎨 Quality Testing

### **Extraction Quality Tests**
```bash
# Test extraction quality
python tests/quality/test_extraction_quality.py

# Test site learning quality
python tests/quality/test_site_learning_quality.py

# Test AI description quality
python tests/quality/test_ai_descriptions.py
```

### **Content Validation Tests**
```bash
# Test content completeness
python tests/quality/test_content_completeness.py

# Test noise removal
python tests/quality/test_noise_removal.py

# Test metadata extraction
python tests/quality/test_metadata_extraction.py
```

---

## 🧪 Test Data Management

### **Test URLs**
```python
# tests/fixtures/test_urls.py
TEST_URLS = {
    "simple": "https://example.com/simple-article",
    "complex": "https://example.com/complex-article",
    "javascript": "https://example.com/spa-article",
    "wordpress": "https://example.com/wordpress-article",
    "medium": "https://example.com/medium-article"
}
```

### **Test Configurations**
```python
# tests/fixtures/test_configs.py
TEST_CONFIGS = {
    "example.com": {
        "selector": "div.content",
        "exclude_selectors": ["nav", "footer"],
        "requires_browser": False
    },
    "spa-site.com": {
        "selector": "body",
        "exclude_selectors": ["nav", "footer", "sidebar"],
        "requires_browser": True
    }
}
```

### **Test Data Cleanup**
```bash
# Clean up test data
python tests/cleanup_test_data.py

# Reset test database
psql -U article_user -d article_extraction_test -c "TRUNCATE TABLE jobs, users, site_configs;"
```

---

## 🔧 Test Configuration

### **Environment Setup**
```bash
# Set up test environment
export TESTING=true
export DATABASE_URL=postgresql://test_user:test_pass@localhost:5432/article_extraction_test
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=1
```

### **Test Database Setup**
```bash
# Create test database
sudo -u postgres createdb article_extraction_test

# Run test migrations
for migration in shared/db/migrations/*.sql; do
    psql -U postgres -d article_extraction_test -f "$migration"
done
```

### **Test Redis Setup**
```bash
# Use separate Redis database for tests
redis-cli -n 1 flushdb
```

---

## 📊 Test Reporting

### **Coverage Reports**
```bash
# Generate Python coverage report
python -m pytest --cov=src --cov-report=html tests/

# Generate Go coverage report
cd api && go test -coverprofile=coverage.out ./...
cd api && go tool cover -html=coverage.out

# Generate frontend coverage report
cd frontend && npm run test:coverage
```

### **Performance Reports**
```bash
# Generate performance report
python tests/performance/generate_report.py

# Generate quality report
python tests/quality/generate_quality_report.py
```

### **Test Results**
```bash
# View test results
cat test_results.json | jq '.'

# View coverage summary
cat coverage_summary.txt
```

---

## 🐛 Debugging Tests

### **Python Test Debugging**
```bash
# Run tests with debug output
python -m pytest -v -s tests/

# Run specific test with debug
python -m pytest -v -s tests/test_extraction.py::test_extract_article

# Run with pdb
python -m pytest --pdb tests/
```

### **Go Test Debugging**
```bash
# Run tests with verbose output
cd api && go test -v ./...

# Run specific test
cd api && go test -v ./internal/handlers -run TestExtractSingle

# Run with race detection
cd api && go test -race ./...
```

### **Frontend Test Debugging**
```bash
# Run tests with debug output
cd frontend && npm test -- --verbose

# Run specific test
cd frontend && npm test -- --testNamePattern="ExtractArticle"
```

---

## 🎯 Test Automation

### **CI/CD Pipeline**
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python -m pytest tests/
```

### **Test Scripts**
```bash
# Run all tests
./scripts/run_all_tests.sh

# Run specific test suite
./scripts/run_unit_tests.sh
./scripts/run_integration_tests.sh
./scripts/run_e2e_tests.sh

# Run performance tests
./scripts/run_performance_tests.sh
```

---

## 📈 Test Metrics

### **Coverage Metrics**
- **Line Coverage** - Percentage of lines executed
- **Branch Coverage** - Percentage of branches executed
- **Function Coverage** - Percentage of functions executed

### **Performance Metrics**
- **Response Time** - API response time
- **Throughput** - Requests per second
- **Memory Usage** - Memory consumption
- **CPU Usage** - CPU utilization

### **Quality Metrics**
- **Extraction Accuracy** - Percentage of correct extractions
- **Content Completeness** - Percentage of complete content
- **Noise Removal** - Percentage of noise removed
- **Metadata Accuracy** - Percentage of correct metadata

---

## 🎯 Best Practices

### **Test Writing**
- Write tests before code (TDD)
- Use descriptive test names
- Test one thing at a time
- Use meaningful assertions
- Keep tests independent

### **Test Maintenance**
- Update tests when code changes
- Remove obsolete tests
- Keep test data current
- Monitor test performance
- Document test procedures

### **Test Organization**
- Group related tests
- Use test fixtures
- Separate unit and integration tests
- Use test data factories
- Keep tests fast

---

## 📚 Test Resources

### **Testing Tools**
- **Python**: pytest, coverage, mock
- **Go**: testing, testify, go-mock
- **Frontend**: Jest, React Testing Library
- **API**: curl, Postman, Newman
- **Performance**: ab, wrk, k6

### **Test Data**
- **Sample URLs** - Test extraction on various sites
- **Mock Data** - Simulate API responses
- **Test Configurations** - Site-specific extraction rules
- **Expected Results** - Known good extraction outputs

---

## 🎉 Test Success Criteria

### **Unit Tests**
- [ ] All functions have tests
- [ ] Test coverage > 80%
- [ ] Tests run in < 30 seconds
- [ ] No flaky tests

### **Integration Tests**
- [ ] All components integrate correctly
- [ ] Database operations work
- [ ] API endpoints respond correctly
- [ ] Workers process jobs

### **End-to-End Tests**
- [ ] Complete workflows work
- [ ] User scenarios are covered
- [ ] Error handling works
- [ ] Performance is acceptable

---

**Testing ensures the Article Extraction System works reliably and efficiently!**



