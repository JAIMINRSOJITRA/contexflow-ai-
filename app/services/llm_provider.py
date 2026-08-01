"""LLM answer-generation using direct SDKs — no LangChain.

Gemini is called via the google-genai SDK (same as document_processor.py).
Groq is called via the groq SDK.

Everything outside this file calls only generate_answer(prompt, provider) —
the provider-specific details are fully contained here.

Includes retry logic with exponential backoff for transient failures.
"""
import time
from app.core.config import DEFAULT_LLM_PROVIDER, GEMINI_API_KEY, GROQ_API_KEY, GEMINI_MODEL, GROQ_MODEL

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1  # seconds
MAX_RETRY_DELAY = 10  # seconds


def _retry_with_backoff(func, *args, **kwargs):
    """Execute function with exponential backoff on transient failures."""
    delay = INITIAL_RETRY_DELAY
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            
            # Only retry on transient errors (rate limit, timeout, connection)
            is_retryable = any(
                keyword in error_str
                for keyword in ["rate limit", "timeout", "connection", "503", "429", "500"]
            )
            
            if not is_retryable or attempt == MAX_RETRIES - 1:
                raise
            
            # Exponential backoff with jitter
            time.sleep(delay)
            delay = min(delay * 2, MAX_RETRY_DELAY)
    
    raise last_error


def _gemini_answer(prompt: str) -> str:
    """Send a prompt to Gemini and return the plain-text response."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is missing or set to its placeholder value. "
            "Add a real key to your .env file."
        )
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "Gemini generation requires the google-genai package. "
            "Run: pip install -r requirements.txt"
        ) from exc

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return (response.text or "").strip()


def _groq_answer(prompt: str) -> str:
    """Send a prompt to Groq and return the plain-text response."""
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        raise ValueError(
            "GROQ_API_KEY is missing or set to its placeholder value. "
            "Add a real key to your .env file."
        )
    try:
        from groq import Groq
    except ImportError as exc:
        raise RuntimeError(
            "Groq generation requires the groq package. "
            "Run: pip install -r requirements.txt"
        ) from exc

    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return (response.choices[0].message.content or "").strip()


def generate_answer(prompt: str, provider: str | None = None) -> str:
    """Invoke Gemini or Groq through one provider-independent interface.

    Switching providers is a one-word change at the call site (or in .env).
    All provider-specific API differences live inside _gemini_answer and
    _groq_answer — nothing outside this file needs to change.
    
    Includes automatic retry with exponential backoff for transient failures.
    """
    provider = provider or DEFAULT_LLM_PROVIDER
    if provider == "gemini":
        return _retry_with_backoff(_gemini_answer, prompt)
    if provider == "groq":
        return _retry_with_backoff(_groq_answer, prompt)
    raise ValueError(
        f"Unknown provider '{provider}'. Must be 'gemini' or 'groq'."
    )
