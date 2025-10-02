# Contributing to Article Extractor

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

---

## How to Contribute

### 1. Reporting Issues

If you find a bug or have a feature request:

1. **Search existing issues** to avoid duplicates
2. **Create a new issue** with:
   - Clear, descriptive title
   - Detailed description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - System information (OS, Python version)
   - Example URLs if relevant

### 2. Submitting Code

#### Before You Start

1. **Fork the repository**
2. **Create a new branch** from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Set up development environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

#### Development Guidelines

**Code Style:**
- Follow PEP 8 Python style guide
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small

**Documentation:**
- Update relevant documentation in `docs/`
- Add comments for complex logic
- Update README.md if adding new features
- Include usage examples

**Testing:**
- Test your changes thoroughly
- Add test cases for new features
- Ensure existing tests still pass
- Test with multiple URLs if relevant

#### Making Changes

1. **Write your code**
   - Follow the coding standards
   - Keep commits focused and atomic
   - Write clear commit messages

2. **Test thoroughly**
   ```bash
   # Test basic extraction
   python3 -m src.article_extractor https://example.com/article
   
   # Test with AI descriptions
   python3 -m src.article_extractor --gemini https://example.com/article
   
   # Run existing tests
   python3 -m tests.test_gemini_vision
   ```

3. **Update documentation**
   - Update relevant files in `docs/`
   - Add usage examples
   - Update CHANGELOG.md

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: Add support for X"
   ```

#### Commit Message Format

Use conventional commits format:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, no logic change)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

**Examples:**
```
feat(extractor): Add support for PDF export
fix(gemini): Handle rate limit errors correctly
docs(readme): Update installation instructions
```

### 3. Submitting Pull Request

1. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Open a Pull Request**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your branch
   - Fill in the PR template

3. **PR Description should include:**
   - What changed and why
   - Related issue numbers (#123)
   - Testing done
   - Screenshots/examples if relevant
   - Breaking changes (if any)

4. **Respond to feedback**
   - Address review comments
   - Make requested changes
   - Push updates to same branch

---

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Virtual environment tool
- Git

### Setup Steps

```bash
# 1. Clone your fork
git clone https://github.com/YOUR_USERNAME/article-extractor.git
cd article-extractor

# 2. Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/article-extractor.git

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Copy config template
cp config/config.json.template config/config.json
# Edit config.json and add your Gemini API key

# 6. Test installation
python3 -m src.article_extractor --help
```

### Keeping Your Fork Updated

```bash
# Fetch upstream changes
git fetch upstream

# Merge into your main branch
git checkout main
git merge upstream/main

# Push to your fork
git push origin main
```

---

## Code Review Process

1. **Automated checks** run on every PR
   - Code style validation
   - Basic functionality tests

2. **Maintainer review**
   - Code quality
   - Documentation completeness
   - Test coverage
   - Adherence to guidelines

3. **Feedback and iteration**
   - Address comments
   - Make improvements
   - Discuss alternatives

4. **Approval and merge**
   - Maintainer approves
   - PR is merged to main

---

## Areas for Contribution

### High Priority

- 🐛 **Bug Fixes** - Fix reported issues
- 📝 **Documentation** - Improve guides and examples
- 🧪 **Testing** - Add test cases
- ♿ **Accessibility** - Improve description quality

### Feature Ideas

- 🌐 **Multi-site Support** - Support more websites
- 📄 **Export Formats** - PDF, EPUB, HTML output
- 🔌 **Plugin System** - Custom parsers and processors
- 🖼️ **Image Handling** - Download and embed images
- 🌍 **Internationalization** - Multi-language support
- 🐳 **Docker** - Containerization
- 🌐 **Web Interface** - Browser-based UI
- 🔄 **Batch Improvements** - Parallel processing
- 💾 **Caching** - Cache API responses
- 📊 **Analytics** - Processing statistics

### Documentation Improvements

- More usage examples
- Video tutorials
- Architecture diagrams
- Performance benchmarks
- Troubleshooting guides

---

## Style Guide

### Python Code

```python
# Good
def extract_article(url: str) -> dict:
    """
    Extract article content from URL.
    
    Args:
        url: The article URL to extract
        
    Returns:
        dict: Extracted article data with title, content, images
        
    Raises:
        ValueError: If URL is invalid
        RequestException: If download fails
    """
    if not url.startswith('http'):
        raise ValueError("Invalid URL")
    
    # Implementation
    pass

# Bad
def extract(u):
    # Extract article
    pass
```

### Documentation

```markdown
# Good
## Feature Name

Brief description of what this feature does.

### Usage

\`\`\`bash
python3 -m src.article_extractor --option value
\`\`\`

### Options

- `--option` - Description of option

### Example

Concrete example with expected output.

# Bad
## Feature

Does stuff.
```

---

## Getting Help

- 💬 **Questions?** Open a discussion
- 🐛 **Found a bug?** Open an issue
- 💡 **Have an idea?** Open a feature request
- 🤝 **Want to chat?** Join our community

---

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in relevant documentation

---

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Provide constructive feedback
- Focus on the best outcome for the project
- Be patient with review process

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing! 🎉**

