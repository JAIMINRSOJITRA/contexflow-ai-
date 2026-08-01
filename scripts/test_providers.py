"""
Test script to verify Groq and Gemini LLM providers work end-to-end.

Usage:
    python scripts/test_providers.py
"""
import sys
from pathlib import Path

# Add project root to Python path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(override=True)

from app.services.llm_provider import generate_answer


def test_gemini():
    """Test Gemini provider."""
    print("🧪 Testing Gemini provider...")
    try:
        answer = generate_answer("What is 2 + 2? Answer in one sentence.", provider="gemini")
        print(f"✅ Gemini response: {answer}")
        return True
    except Exception as e:
        print(f"❌ Gemini failed: {e}")
        return False


def test_groq():
    """Test Groq provider."""
    print("\n🧪 Testing Groq provider...")
    try:
        answer = generate_answer("What is 2 + 2? Answer in one sentence.", provider="groq")
        print(f"✅ Groq response: {answer}")
        return True
    except Exception as e:
        print(f"❌ Groq failed: {e}")
        return False


def main():
    """Run all provider tests."""
    print("=" * 60)
    print("LLM Provider Test Suite")
    print("=" * 60)
    
    gemini_ok = test_gemini()
    groq_ok = test_groq()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    print(f"Gemini: {'✅ PASS' if gemini_ok else '❌ FAIL'}")
    print(f"Groq:   {'✅ PASS' if groq_ok else '❌ FAIL'}")
    
    if gemini_ok and groq_ok:
        print("\n🎉 All providers working!")
        sys.exit(0)
    else:
        print("\n⚠️  Some providers failed. Check your API keys in .env")
        sys.exit(1)


if __name__ == "__main__":
    main()
