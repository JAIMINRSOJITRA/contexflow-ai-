# ContextFlow AI Project Blueprint

## Product Goal

ContextFlow AI gives a person a dependable way to ask questions about a small collection of private documents. It should make the document set visible, identify the sources behind each answer, and make it possible to remove unwanted documents without resetting the whole system.

## Supported User Workflows

1. Configure Gemini and, optionally, Groq credentials in `.env`.
2. Upload a `.txt`, `.pdf`, or `.docx` file.
3. Confirm the upload appears in `GET /api/v1/documents`.
4. Ask a question with `POST /api/v1/chat/ask`.
5. Inspect the answer's source filenames and reuse the session ID for history.
6. Rate an answer through `POST /api/v1/feedback`.
7. Delete a document when it is obsolete or incorrect.
8. Evaluate representative question-answer-context samples before changing retrieval settings.

## System Design

### Ingestion

- `.txt` files are decoded as UTF-8.
- Text-based `.pdf` files are extracted locally with PyMuPDF; scanned PDFs fall back to Gemini vision.
- `.docx` files are read with python-docx, including paragraphs and table cells.
- Text is divided into overlapping character chunks using `CHUNK_SIZE` and `CHUNK_OVERLAP`.
- Gemini produces one embedding for each chunk by default. Sentence-Transformers is an environment-configured local fallback.
- FAISS persists the embedding vectors. SQLite persists document metadata.
- Each upload gets a stable internal source ID. FAISS keeps that ID for deletion while answers show the original human-readable filename.

### Question Answering

- An empty vector index returns an upload prompt before any provider call.
- The question is embedded with Gemini.
- FAISS returns the `TOP_K_RESULTS` nearest chunks.
- The prompt directs the selected answer provider to use only the returned context and acknowledge missing information instead of guessing.
- The API returns the answer, unique source filenames, actual provider, session ID, message ID, and end-to-end latency in milliseconds.

### Persistence

| Store | Contents |
| --- | --- |
| SQLite | Document metadata, chat messages, feedback |
| FAISS index | Embedding vectors |
| FAISS metadata | Chunk text, display filename, internal document ID |
| Upload directory | Original uploaded files under a generated safe filename |

Deleting a document removes its metadata, its stored upload, and only the matching FAISS chunks. The flat FAISS index is rebuilt from retained vectors to keep vector and metadata positions aligned.

## API Contract Principles

- Invalid user input receives a `400` response.
- Unknown documents and messages receive `404`.
- Missing provider configuration receives `503` with an actionable description.
- Unexpected provider failures receive `502` rather than exposing an internal traceback.
- Every request and response uses a Pydantic model where a shared API shape exists.

## Evaluation

The evaluation API reports the common RAG metrics: faithfulness, answer relevancy, context precision, and context recall through Ragas. It uses LangChain's Gemini adapters for the evaluator model and embeddings. Scores are LLM-assisted quality signals rather than deterministic tests.

Use `scripts/run_evaluation.py` as a starting sample set. Replace its questions, answers, and retrieved contexts with representative cases before tuning chunking, `TOP_K_RESULTS`, prompts, or model selection.

## Operational Notes

- `DATABASE_URL`, vector paths, and other behavior are configured through environment variables; source edits are not required for ordinary tuning.
- The database initializer creates current tables and adds the document storage fields to an existing SQLite database on startup.
- `scripts/reset_db.py` requires confirmation and clears database records plus vector data. It intentionally leaves uploads on disk so a reset does not silently destroy source files.
- Docker Compose persists all runtime state in a named `app_data` volume.

## Current Boundaries

- No authentication, authorization, tenant isolation, quotas, or rate limiting.
- No asynchronous job queue; large PDFs are processed during the upload request.
- Scanned-PDF OCR and default embeddings require Gemini even if Groq handles answer generation. Text PDFs, DOCX extraction, and Sentence-Transformers embeddings can run locally.
- FAISS is local disk storage, appropriate for one local deployment rather than concurrent distributed writers.
- There is no document versioning or per-user ownership yet.

## Next Priorities

1. Add authentication and ownership before exposing the API beyond a trusted environment.
2. Add background ingestion with progress reporting for larger documents.
3. Add document versioning and duplicate detection.
4. Add structured source citations with chunk locations.
5. Add an evaluation dataset and threshold-based regression checks.
6. Move from local SQLite and FAISS to managed services when multi-user deployment is needed.
