"""
interpreter.py - AI Layer for Muse CLI
Handles interaction with Google Gemini for converting abstract text to art search keywords.
"""

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from google import genai
from google.genai import types
from usage_tracker import get_tracker


class InterpreterError(Exception):
    """Custom exception for interpreter errors."""
    pass


class InterpreterTimeoutError(InterpreterError):
    """Raised when the AI model times out."""
    pass


def generate_with_timeout(client, model_name: str, prompt: str, timeout_seconds: int = 30) -> str:
    """
    Generate content with timeout protection.

    Args:
        client: The Google GenAI client instance
        model_name: Name of the model to use
        prompt: The prompt to send to the model
        timeout_seconds: Maximum time to wait for response

    Returns:
        Generated text content

    Raises:
        InterpreterTimeoutError: If the request times out
        InterpreterError: If the request fails
    """
    def _generate():
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=100,
                    system_instruction="You are an art curator. Convert the provided abstract text into a search query for an art database. Focus on visual subjects, art styles, and specific painter names. Return ONLY the search keywords separated by spaces. Do not use markdown."
                )
            )
            return response.text
        except Exception as e:
            raise InterpreterError(f"Generation failed: {str(e)}")

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_generate)
        try:
            result = future.result(timeout=timeout_seconds)
            return result
        except FuturesTimeoutError:
            future.cancel()
            raise InterpreterTimeoutError(f"Request timed out after {timeout_seconds} seconds")
        except Exception as e:
            raise InterpreterError(f"Unexpected error: {str(e)}")


def generate_keywords(text: str, timeout: int = 30) -> str:
    """
    Generate art search keywords from abstract philosophical text.

    Args:
        text: The abstract text to interpret
        timeout: Timeout in seconds (default: 30)

    Returns:
        Space-separated search keywords

    Raises:
        InterpreterError: If API key is missing or generation fails
        InterpreterTimeoutError: If the request times out
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise InterpreterError("GEMINI_API_KEY environment variable not set")

    # Initialize client
    client = genai.Client(api_key=api_key)

    # Model name
    model_name = "gemini-2.0-flash-exp"

    # Generate keywords with timeout
    keywords = generate_with_timeout(client, model_name, text, timeout)

    # Clean up the result (remove any markdown, extra whitespace)
    keywords = keywords.strip().replace("\n", " ").replace("  ", " ")

    # Remove any markdown formatting that might have slipped through
    if keywords.startswith("```") or keywords.startswith("`"):
        keywords = keywords.strip("`").strip()

    # Track API usage (estimate tokens based on text length)
    try:
        input_tokens = len(text.split()) * 1.3  # Rough estimate: ~1.3 tokens per word
        output_tokens = len(keywords.split()) * 1.3
        tracker = get_tracker()
        tracker.track_request(int(input_tokens), int(output_tokens))
    except Exception:
        # Don't fail the request if tracking fails
        pass

    return keywords
