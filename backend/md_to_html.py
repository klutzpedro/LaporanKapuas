"""Markdown -> HTML helper."""
import markdown as _md


def md_to_html(text: str) -> str:
    if not text:
        return ""
    # If already HTML-ish, return as-is
    if "<p" in text or "<h" in text or "<strong" in text:
        return text
    return _md.markdown(text, extensions=["extra", "nl2br"])
