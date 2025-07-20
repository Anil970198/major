import re
import markdown

def strip_html_tags(text):
    if not text:
        return ""
    # Remove scripts/styles and HTML tags
    text = re.sub(r"(?is)<(script|style).*?>.*?(</\1>)", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()

def markdownify(text):
    """
    Cleans raw HTML and converts to Markdown-styled HTML for safe rendering.
    """
    cleaned = strip_html_tags(text)
    return markdown.markdown(cleaned, extensions=["extra", "sane_lists"])
