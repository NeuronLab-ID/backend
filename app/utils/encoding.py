import base64


def decode_base64_if_needed(text: str) -> str:
    """Decode Base64 string if it appears to be encoded."""
    if not text:
        return text
    try:
        decoded = base64.b64decode(text).decode('utf-8')
        if decoded.isprintable() or '\n' in decoded:
            return decoded
    except Exception:
        pass
    return text
