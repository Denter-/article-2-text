# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2025-10-02

### 🎉 Initial Release

#### Added
- ✨ Complete article extraction system
- 🤖 Google Gemini Vision API integration for AI-powered image descriptions
- 📝 Context-based image descriptions (free alternative)
- 🎯 Smart UI element filtering (skips logos, buttons, navigation)
- 📊 Detailed descriptions for charts, graphs, tables, and diagrams
- 🔄 Batch processing support for multiple articles
- 💾 Markdown output with professional formatting
- 📁 Organized project structure with docs, tests, scripts
- 📖 Comprehensive documentation
- 🧪 Test scripts for API validation
- 🛠️ Convenience bash scripts for batch processing

#### Features
- **AI Image Descriptions**
  - Powered by Gemini 2.5 Flash
  - Context-aware analysis
  - Filters out UI elements automatically
  - Detailed chart and graph descriptions
  - Cost-effective (~$0.25-0.50 per article)

- **Batch Processing**
  - Process multiple articles from URL list
  - Automatic error handling
  - Progress tracking
  - Summary reports
  - Continue on individual failures

- **Professional Output**
  - Clean Markdown formatting
  - Metadata extraction (title, author, date)
  - Numbered image descriptions
  - Accessible for text-to-speech

- **Developer-Friendly**
  - Modular architecture
  - Well-documented code
  - Easy to extend
  - Test scripts included

#### Documentation
- Complete README with quick start
- Documentation hub with organized sections
- Installation and setup guides
- Usage examples and best practices
- Technical architecture documentation
- API integration details
- Validation reports
- Contributing guidelines

#### Project Structure
```
business_articles/
├── src/              # Source code
├── tests/            # Test scripts
├── scripts/          # Utility scripts
├── config/           # Configuration files
├── results/          # Output directory
├── logs/             # Application logs
└── docs/             # Documentation
    ├── getting-started/
    ├── usage/
    ├── technical/
    └── reference/
```

#### Supported Websites
- ForEntrepreneurs.com (optimized)
- Generic HTML article support

---

## [Unreleased]

### Planned Features
- [ ] PDF export
- [ ] Support for more websites
- [ ] Image download option
- [ ] Web interface
- [ ] Multi-language support
- [ ] Docker containerization
- [ ] Parallel processing
- [ ] API response caching
- [ ] Custom parser plugins

---

## Version History

### Version 1.0.0 (2025-10-02)
- Initial public release
- Core extraction functionality
- Gemini Vision integration
- Complete documentation
- Professional project structure

---

## Migration Guides

### From Development Version

If you were using the development version before 1.0.0:

1. **Update file paths:**
   - `article_extractor.py` → `src/article_extractor.py`
   - Use module import: `python3 -m src.article_extractor`

2. **Update URL list:**
   - Move `forentrepreneurs_urls.txt` → `config/urls.txt`

3. **Update scripts:**
   - Scripts moved to `scripts/` directory
   - Update references in any custom scripts

4. **Update documentation paths:**
   - All docs now in `docs/` directory
   - See `docs/index.md` for navigation

---

## Support

- **Documentation:** [docs/index.md](docs/index.md)
- **Issues:** GitHub Issues
- **Questions:** GitHub Discussions

---

**Note:** This project follows [Semantic Versioning](https://semver.org/):
- MAJOR version for incompatible API changes
- MINOR version for new functionality (backward compatible)
- PATCH version for bug fixes (backward compatible)

