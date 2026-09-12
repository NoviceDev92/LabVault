import re

def slugify(text: str) -> str:
    """Convert a string to a URL-safe slug."""
    # Convert to lowercase
    text = text.lower()
    # Replace non-alphanumeric characters with hyphens
    text = re.sub(r'[^a-z0-9]+', '-', text)
    # Strip leading and trailing hyphens
    text = text.strip('-')
    return text
