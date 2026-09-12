def format_bytes(size_bytes: int) -> str:
    """Format bytes to a human-readable string (e.g., '42.1 MB')."""
    if size_bytes == 0:
        return "0 B"
    
    suffixes = ("B", "KB", "MB", "GB", "TB")
    size = float(size_bytes)
    
    for suffix in suffixes:
        if size < 1024.0:
            if suffix == "B":
                return f"{int(size)} {suffix}"
            return f"{size:.1f} {suffix}"
        size /= 1024.0
        
    return f"{size:.1f} PB"
