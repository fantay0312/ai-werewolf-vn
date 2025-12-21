import logging

logger = logging.getLogger(__name__)

def count_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a text string.
    This is a simple heuristic: 1 token ~= 1.5 characters for Chinese/English mix.
    For more accuracy, we would use tiktoken, but this is sufficient for budget control.
    """
    if not text:
        return 0
    return int(len(text) / 1.5)

def truncate_to_token_limit(text: str, limit: int) -> str:
    """
    Truncate text to fit within a token limit.
    """
    current_tokens = count_tokens(text)
    if current_tokens <= limit:
        return text
    
    # Rough truncation
    ratio = limit / current_tokens
    new_len = int(len(text) * ratio)
    return text[:new_len] + "...(truncated)"
