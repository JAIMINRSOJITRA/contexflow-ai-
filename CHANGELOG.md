# Changelog

All notable changes to ContextFlow AI will be documented in this file.

## [0.3.0] - 2026-08-01

### 🚀 Major Improvements

#### Performance
- **FAISS Index Caching**: Added in-memory caching to avoid reloading index from disk on every operation (10x+ faster searches)
- **Reduced I/O Operations**: Index and metadata now cached globally across requests

#### Stability & Error Handling
- **Streamlit Cloud Compatibility**: Fixed database initialization errors on ephemeral filesystems
- **Graceful Degradation**: Database queries now return empty lists instead of crashing when tables don't exist
- **Retry Logic**: Added automatic retry with exponential backoff for transient API failures
- **Embedding Provider Validation**: Prevents dimension mismatch errors by tracking which provider created the index

#### Security & Validation
- **File Size Limits**: Added 50MB maximum upload size to prevent memory issues
- **Question Length Limits**: Maximum 1000 characters per question
- **Better Error Messages**: API key validation now provides actionable error messages

### ✅ Bug Fixes
- Fixed test isolation issues with FAISS cache
- Fixed SQLite database initialization on Streamlit Cloud
- Fixed embedding provider mismatch crashes
- All 45 tests now passing

### 📝 Configuration
- **New Config Options**:
  - `HYBRID_SEARCH_MULTIPLIER`: Control hybrid search candidate count (default: 3)
  - `RRF_K`: Reciprocal Rank Fusion constant (default: 60)
  - `GEMINI_MODEL`: Configurable Gemini model name (default: gemini-2.5-flash)
  - `GROQ_MODEL`: Configurable Groq model name (default: llama-3.3-70b-versatile)

### 🧪 Testing
- Added provider test script: `python scripts/test_providers.py`
- Both Gemini and Groq providers confirmed working
- Test suite expanded with cache invalidation

### 📚 Documentation
- Created SECURITY_NOTICE.md with API key best practices
- Created FIXES_APPLIED.md documenting all changes
- Updated README with security warnings and deployment notes
- Added CHANGELOG.md (this file)

---

## [0.2.0] - 2026-08-01 (Earlier)

### Added
- Streamlit frontend (`app.py`) for HuggingFace Spaces deployment
- Hybrid search with RRF (Reciprocal Rank Fusion)
- HyDE query expansion support
- Enterprise-grade RAG prompting with Chain-of-Thought
- Ragas evaluation framework integration
- Comprehensive test suite (45 tests)

### Changed
- Removed LangChain from main pipeline (direct SDK usage)
- Removed Docker and deployment configs (Dockerfile, docker-compose, Procfile, render.yaml, railway.json)
- FastAPI now API-only (no static file serving)

### Fixed
- Missing dependencies: sentence-transformers, faiss-cpu
- Duplicate database files
- Static file serving errors in FastAPI

---

## [0.1.0] - Initial Release

### Added
- FastAPI backend with REST APIs
- Document upload (PDF, TXT, DOCX)
- Text extraction with Gemini Vision OCR for PDFs
- FAISS vector store
- RAG question answering
- Chat history and sessions
- Feedback system
- SQLite database
- Gemini and Groq LLM providers
- Sentence-transformers local embeddings

---

**Legend:**
- 🚀 Major Improvements
- ✅ Bug Fixes
- 📝 Configuration
- 🧪 Testing
- 📚 Documentation
