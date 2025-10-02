import re


def sanitize_md(text: str, in_heading_context: bool = False) -> str:
    """
    NOTE: meant for Discord-flavored markdown
    """
    if in_heading_context:
        # Only escape heading-style # at start of line (1-3 # followed by a space)
        text = re.sub(
            r"^(#{1,3})(?=\s)",
            lambda m: "\\" * len(m.group(1)) + m.group(1),
            text,
            flags=re.MULTILINE,
        )

    # Don't double-escape if already escaped
    sanitized_text = re.sub(r"([\\*_~|`])", r"\\\1", text)
    return sanitized_text
