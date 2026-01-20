import re
import logging
from typing import List, Dict, Tuple

from utils.constants import (
    TAG_KEYWORDS, 
    TAG_CATEGORIES,
    POSITIVE_KEYWORDS,
    NEGATIVE_KEYWORDS,
    NEGATION_WORDS
)
from utils.validators import has_negation_before
from utils.cache import cache_async, tag_extraction_key

logger = logging.getLogger(__name__)


# ============================================================================
# TAG EXTRACTION (Using centralized tags - Issue #6)
# ============================================================================

@cache_async(ttl=1800, key_func=lambda text: tag_extraction_key(text))
async def extract_tags_from_text(text: str) -> List[str]:
    """
    Extract relevant tags from user's text using keyword matching.
    CACHED for 30 minutes (Issue #15)
    
    Args:
        text: User's text input (notes, reflections, answers)
    
    Returns:
        List of tags found in the text
    """
    if not text or len(text.strip()) < 3:
        return []
    
    text_lower = text.lower()
    text_lower = re.sub(r'[^\w\s]', ' ', text_lower)  # Remove punctuation
    
    found_tags = []
    
    # Check each tag category (from constants.py)
    for tag, keywords in TAG_KEYWORDS.items():
        # Check if any keyword appears in text
        for keyword in keywords:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower):
                found_tags.append(tag)
                break  # Only add tag once per category
    
    return found_tags


def extract_tags_sync(text: str) -> List[str]:
    """
    Synchronous version of tag extraction (for non-async contexts).
    
    Args:
        text: User's text input
    
    Returns:
        List of tags found
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(extract_tags_from_text(text))
    except RuntimeError:
        # If no event loop, run without cache
        return _extract_tags_no_cache(text)


def _extract_tags_no_cache(text: str) -> List[str]:
    """Internal: Extract tags without caching."""
    if not text or len(text.strip()) < 3:
        return []
    
    text_lower = text.lower()
    text_lower = re.sub(r'[^\w\s]', ' ', text_lower)
    
    found_tags = []
    
    for tag, keywords in TAG_KEYWORDS.items():
        for keyword in keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower):
                found_tags.append(tag)
                break
    
    return found_tags


# ============================================================================
# SENTIMENT ANALYSIS (IMPROVED - Issue #14)
# ============================================================================

def analyze_sentiment(text: str) -> str:
    """
    IMPROVED: Analyze sentiment with negation handling.
    
    Args:
        text: User's text input
    
    Returns:
        "positive", "negative", or "neutral"
    """
    if not text or len(text.strip()) < 3:
        return "neutral"
    
    text_lower = text.lower()
    
    # Count positive and negative keywords with negation awareness
    positive_count = 0
    negative_count = 0
    
    for word in POSITIVE_KEYWORDS:
        if word in text_lower:
            # Check if negated (e.g., "not happy")
            if has_negation_before(text_lower, word):
                negative_count += 1  # Negated positive = negative
            else:
                positive_count += 1
    
    for word in NEGATIVE_KEYWORDS:
        if word in text_lower:
            # Check if negated (e.g., "not bad")
            if has_negation_before(text_lower, word):
                positive_count += 1  # Negated negative = positive
            else:
                negative_count += 1
    
    # Determine sentiment
    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    else:
        return "neutral"


def get_sentiment_score(text: str) -> float:
    """
    Get numerical sentiment score.
    
    Args:
        text: User's text input
    
    Returns:
        Score from -1.0 (negative) to +1.0 (positive)
    """
    if not text or len(text.strip()) < 3:
        return 0.0
    
    text_lower = text.lower()
    
    positive_count = 0
    negative_count = 0
    
    for word in POSITIVE_KEYWORDS:
        if word in text_lower:
            if has_negation_before(text_lower, word):
                negative_count += 1
            else:
                positive_count += 1
    
    for word in NEGATIVE_KEYWORDS:
        if word in text_lower:
            if has_negation_before(text_lower, word):
                positive_count += 1
            else:
                negative_count += 1
    
    total = positive_count + negative_count
    if total == 0:
        return 0.0
    
    return (positive_count - negative_count) / total


# ============================================================================
# TAG ANALYSIS (Using centralized categories - Issue #6)
# ============================================================================

def count_tag_frequency(tags_list: List[List[str]]) -> Dict[str, int]:
    """
    Count frequency of tags across multiple entries.
    
    Args:
        tags_list: List of tag lists from multiple entries
    
    Returns:
        Dictionary with tag counts
    """
    frequency = {}
    
    for tags in tags_list:
        for tag in tags:
            frequency[tag] = frequency.get(tag, 0) + 1
    
    return frequency


def get_top_tags(frequency: Dict[str, int], limit: int = 5) -> List[Tuple[str, int]]:
    """
    Get top N most frequent tags.
    
    Args:
        frequency: Tag frequency dictionary
        limit: Number of top tags to return
    
    Returns:
        List of (tag, count) tuples sorted by frequency
    """
    sorted_tags = sorted(frequency.items(), key=lambda x: x[1], reverse=True)
    return sorted_tags[:limit]


def categorize_tags(tags: List[str]) -> Dict[str, List[str]]:
    """
    Group tags by category using centralized categories.
    
    Args:
        tags: List of tags
    
    Returns:
        Dictionary with categorized tags
    """
    categories = {
        'stressors': [],
        'positive_activities': [],
        'sleep_issues': [],
        'mood_factors': [],
        'other': []
    }
    
    for tag in tags:
        if tag in TAG_CATEGORIES['stressor']:
            categories['stressors'].append(tag)
        elif tag in TAG_CATEGORIES['activity']:
            categories['positive_activities'].append(tag)
        elif tag in TAG_CATEGORIES['sleep']:
            categories['sleep_issues'].append(tag)
        elif tag in TAG_CATEGORIES['mood']:
            categories['mood_factors'].append(tag)
        else:
            categories['other'].append(tag)
    
    return categories


def format_tags_for_display(tags: List[str]) -> str:
    """
    Format tags for user-friendly display.
    
    Args:
        tags: List of tags
    
    Returns:
        Formatted string
    """
    if not tags:
        return "No specific themes detected"
    
    # Convert snake_case to Title Case
    formatted = [tag.replace('_', ' ').title() for tag in tags]
    
    return ", ".join(formatted)


# ============================================================================
# ANALYSIS HELPERS
# ============================================================================

def extract_key_phrases(text: str, max_phrases: int = 3) -> List[str]:
    """
    Extract key phrases from text (simple implementation).
    
    Args:
        text: User's text
        max_phrases: Maximum number of phrases to extract
    
    Returns:
        List of key phrases
    """
    if not text or len(text) < 20:
        return []
    
    # Split into sentences
    sentences = re.split(r'[.!?]+', text)
    
    # Get first few short sentences (5-15 words)
    key_phrases = []
    for sentence in sentences:
        words = sentence.strip().split()
        if 5 <= len(words) <= 15:
            key_phrases.append(sentence.strip())
            if len(key_phrases) >= max_phrases:
                break
    
    return key_phrases


def calculate_text_complexity(text: str) -> str:
    """
    Calculate complexity level of user's text.
    
    Args:
        text: User's text
    
    Returns:
        "brief", "moderate", or "detailed"
    """
    if not text:
        return "brief"
    
    word_count = len(text.split())
    
    if word_count < 10:
        return "brief"
    elif word_count < 50:
        return "moderate"
    else:
        return "detailed"


def analyze_text_metrics(text: str) -> Dict[str, any]:
    """
    Get comprehensive text metrics.
    
    Args:
        text: User's text
    
    Returns:
        Dictionary with various metrics
    """
    if not text:
        return {
            'word_count': 0,
            'char_count': 0,
            'sentence_count': 0,
            'complexity': 'brief',
            'sentiment': 'neutral',
            'sentiment_score': 0.0
        }
    
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    
    return {
        'word_count': len(words),
        'char_count': len(text),
        'sentence_count': len([s for s in sentences if s.strip()]),
        'complexity': calculate_text_complexity(text),
        'sentiment': analyze_sentiment(text),
        'sentiment_score': get_sentiment_score(text)
    }