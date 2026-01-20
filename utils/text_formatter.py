import re
from typing import Optional


def markdown_to_html(text: str) -> str:
    """
    Convert markdown formatting to Telegram HTML.
    
    Handles:
    - **bold** → <b>bold</b>
    - *italic* → <i>italic</i>
    - `code` → <code>code</code>
    - [link](url) → <a href="url">link</a>
    
    Args:
        text: Text with markdown formatting
    
    Returns:
        Text with HTML formatting
    """
    if not text:
        return ""
    
    # Bold: **text** → <b>text</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    
    # Italic: *text* → <i>text</i> (but not ** which was already handled)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    
    # Code: `text` → <code>text</code>
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    
    # Links: [text](url) → <a href="url">text</a>
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    
    # Remove any remaining markdown artifacts
    text = text.replace('*', '')
    
    return text


def clean_ai_response(text: str, max_length: Optional[int] = None) -> str:
    """
    Clean and format AI response for Telegram.
    
    Args:
        text: Raw AI response
        max_length: Optional max length
    
    Returns:
        Cleaned and formatted text
    """
    if not text:
        return ""
    
    # Convert markdown to HTML
    text = markdown_to_html(text)
    
    # Remove excessive newlines (more than 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Trim whitespace
    text = text.strip()
    
    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length-3] + "..."
    
    return text


def format_ai_insights(summary: str, recommendations: str) -> str:
    """
    Format AI insights for weekly report.
    
    Args:
        summary: AI summary text
        recommendations: AI recommendations text
    
    Returns:
        Formatted HTML string
    """
    summary_clean = clean_ai_response(summary)
    recommendations_clean = clean_ai_response(recommendations)
    
    result = f"🤖 <b>AI Insights:</b>\n<i>{summary_clean}</i>\n\n"
    
    if recommendations_clean:
        result += f"💡 <b>Recommendations:</b>\n{recommendations_clean}"
    
    return result