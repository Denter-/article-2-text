# Contributing Guide

**How to contribute to the Article Extraction System**

---

## 🎯 How to Contribute

We welcome contributions! Here's how to get started:

### **Types of Contributions**
- **Bug fixes** - Fix issues and improve stability
- **New features** - Add new extraction methods or capabilities
- **Documentation** - Improve guides and technical documentation
- **Testing** - Add tests and improve test coverage
- **Performance** - Optimize extraction speed and accuracy

---

## 🚀 Getting Started

### **Prerequisites**
- Python 3.8+
- Go 1.21+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Git

### **Step 1: Fork and Clone**
```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/your-username/article-2-text.git
cd article-2-text

# Add upstream remote
git remote add upstream https://github.com/original-owner/article-2-text.git
```

### **Step 2: Set Up Development Environment**
```bash
# Create development branch
git checkout -b feature/your-feature-name

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up Go environment
cd api && go mod download
cd ../worker-go && go mod download

# Set up frontend
cd ../frontend && npm install
```

### **Step 3: Set Up Database**
```bash
# Start PostgreSQL and Redis
sudo systemctl start postgresql redis-server

# Create development database
sudo -u postgres createdb article_extraction_dev

# Run migrations
for migration in shared/db/migrations/*.sql; do
    psql -U postgres -d article_extraction_dev -f "$migration"
done
```

---

## 🧪 Development Workflow

### **Step 1: Make Changes**
```bash
# Make your changes
# Test your changes
python src/article_extractor.py --help

# Run tests
python -m pytest tests/
```

### **Step 2: Test Your Changes**
```bash
# Test Python CLI
python src/article_extractor.py https://example.com/article

# Test API
cd api && go run cmd/api/main.go &
curl http://localhost:8080/health

# Test frontend
cd frontend && npm run dev
```

### **Step 3: Commit Changes**
```bash
# Add your changes
git add .

# Commit with descriptive message
git commit -m "feat: add new extraction method for WordPress sites"

# Push to your fork
git push origin feature/your-feature-name
```

### **Step 4: Create Pull Request**
1. Go to your fork on GitHub
2. Click "New Pull Request"
3. Select your feature branch
4. Add description of your changes
5. Submit the pull request

---

## 📝 Code Standards

### **Python Code Style**
```python
# Use type hints
def extract_article(url: str, config: dict) -> str:
    """Extract article content from URL.
    
    Args:
        url: Article URL to extract
        config: Extraction configuration
        
    Returns:
        Extracted article content
    """
    # Implementation here
    pass

# Use meaningful variable names
article_content = extract_article(url, config)
```

### **Go Code Style**
```go
// Use proper error handling
func ExtractArticle(url string, config Config) (string, error) {
    if url == "" {
        return "", errors.New("URL cannot be empty")
    }
    
    // Implementation here
    return content, nil
}

// Use meaningful function names
func (e *Extractor) ProcessArticle(url string) error {
    // Implementation here
    return nil
}
```

### **JavaScript/TypeScript Style**
```typescript
// Use TypeScript interfaces
interface Article {
  id: string;
  url: string;
  title: string;
  content: string;
}

// Use async/await
async function extractArticle(url: string): Promise<Article> {
  const response = await fetch(`/api/v1/extract/single`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url })
  });
  
  return response.json();
}
```

---

## 🧪 Testing

### **Python Tests**
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_extraction.py

# Run with coverage
python -m pytest --cov=src tests/
```

### **Go Tests**
```bash
# Run API tests
cd api && go test ./...

# Run worker tests
cd worker-go && go test ./...

# Run with coverage
cd api && go test -cover ./...
```

### **Frontend Tests**
```bash
# Run frontend tests
cd frontend && npm test

# Run with coverage
cd frontend && npm run test:coverage
```

### **Integration Tests**
```bash
# Test full workflow
./test_e2e.sh

# Test API endpoints
./test_api.sh

# Test extraction quality
./test_advanced.sh
```

---

## 📚 Documentation

### **Code Documentation**
```python
def learn_site(url: str, max_iterations: int = 3) -> bool:
    """Learn how to extract content from a new site.
    
    This function uses AI to automatically learn extraction rules
    for a new website by analyzing the HTML structure and
    identifying content patterns.
    
    Args:
        url: URL of the article to learn from
        max_iterations: Maximum number of learning attempts
        
    Returns:
        True if learning was successful, False otherwise
        
    Raises:
        ValueError: If URL is invalid
        LearningError: If learning fails after max_iterations
        
    Example:
        >>> success = learn_site("https://example.com/article")
        >>> print(f"Learning successful: {success}")
        Learning successful: True
    """
    # Implementation here
    pass
```

### **API Documentation**
```go
// ExtractArticle extracts article content from a URL
// @Summary Extract article content
// @Description Extract clean article content from a web page
// @Tags extraction
// @Accept json
// @Produce json
// @Param request body ExtractRequest true "Extraction request"
// @Success 200 {object} ExtractResponse
// @Failure 400 {object} ErrorResponse
// @Failure 401 {object} ErrorResponse
// @Router /api/v1/extract/single [post]
func (h *ExtractHandler) ExtractSingle(c *fiber.Ctx) error {
    // Implementation here
}
```

---

## 🐛 Bug Reports

### **Before Reporting**
1. Check if the issue already exists
2. Try to reproduce the issue
3. Check the logs for error messages
4. Test with different URLs

### **Bug Report Template**
```markdown
**Bug Description**
A clear description of what the bug is.

**Steps to Reproduce**
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Environment**
- OS: Ubuntu 20.04
- Python: 3.9.7
- Go: 1.21.0
- Browser: Chrome 91

**Logs**
```
Error message here
```

**Additional Context**
Any other context about the problem.
```

---

## ✨ Feature Requests

### **Feature Request Template**
```markdown
**Feature Description**
A clear description of the feature you'd like to see.

**Use Case**
Why would this feature be useful?

**Proposed Solution**
How do you think this feature should work?

**Alternatives**
Are there any alternative solutions you've considered?

**Additional Context**
Any other context about the feature request.
```

---

## 🔧 Development Tools

### **Python Development**
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run linting
flake8 src/
black src/
isort src/

# Run type checking
mypy src/
```

### **Go Development**
```bash
# Format code
go fmt ./...

# Run linting
golangci-lint run

# Run vet
go vet ./...
```

### **Frontend Development**
```bash
# Install development dependencies
cd frontend && npm install

# Run linting
npm run lint

# Format code
npm run format

# Type checking
npm run type-check
```

---

## 📊 Performance Guidelines

### **Python Performance**
- Use `asyncio` for I/O operations
- Cache expensive computations
- Use generators for large datasets
- Profile with `cProfile`

### **Go Performance**
- Use connection pooling
- Implement proper timeouts
- Use `sync.Pool` for object reuse
- Profile with `pprof`

### **Database Performance**
- Use proper indexes
- Implement connection pooling
- Use prepared statements
- Monitor query performance

---

## 🎯 Contribution Areas

### **High Priority**
- **Site Learning Improvements** - Better AI prompts and validation
- **Performance Optimization** - Faster extraction and processing
- **Error Handling** - Better error messages and recovery
- **Testing** - More comprehensive test coverage

### **Medium Priority**
- **New Extractors** - Support for more site types
- **API Features** - New endpoints and capabilities
- **Frontend Features** - Better user interface
- **Documentation** - More guides and examples

### **Low Priority**
- **Code Refactoring** - Clean up existing code
- **Style Improvements** - Better code formatting
- **Comments** - More inline documentation
- **Examples** - More usage examples

---

## 📚 Resources

### **Learning Resources**
- **[System Architecture](../technical/architecture.md)** - How the system works
- **[Site Learning Process](../technical/site-learning.md)** - How AI learning works
- **[API Reference](../usage/api-reference.md)** - API documentation

### **Development Resources**
- **[Python Documentation](https://docs.python.org/3/)** - Python language reference
- **[Go Documentation](https://golang.org/doc/)** - Go language reference
- **[React Documentation](https://reactjs.org/docs/)** - React framework guide

---

## 🤝 Community

### **Getting Help**
- **GitHub Issues** - Report bugs and request features
- **Discussions** - Ask questions and share ideas
- **Code Review** - Review pull requests and provide feedback

### **Code of Conduct**
- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Follow the project's coding standards

---

## 🎉 Recognition

Contributors will be recognized in:
- **README.md** - Contributor list
- **CHANGELOG.md** - Contribution history
- **Release Notes** - Feature acknowledgments

---

**Thank you for contributing to the Article Extraction System!**



