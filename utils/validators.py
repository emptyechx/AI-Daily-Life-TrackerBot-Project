import re
import pytz
from html import escape
from functools import lru_cache
from typing import Optional, Tuple
from datetime import datetime, timedelta

from utils.constants import (
    NOTIFICATION_MORNING_OFFSET_HOURS,
    NOTIFICATION_DAY_OFFSET_HOURS,
    NOTIFICATION_EVENING_OFFSET_HOURS,
    LANGUAGE_TO_TIMEZONE,
    DEFAULT_TIMEZONE,
    MIN_SLEEP_HOURS,
    MAX_SLEEP_HOURS,
    MSG_INVALID_SLEEP_SCHEDULE,
    NEGATION_WORDS
)


def escape_html(text: str) -> str:
    """Escapes HTML special characters to prevent parsing errors in Telegram."""
    return escape(str(text))


def clean_numeric_input(text: str) -> str:
    """Removes non-numeric characters and normalizes decimal separators."""
    cleaned = re.sub(r'[^0-9.,]', '', text)
    return cleaned.replace(',', '.')


def validate_integer(text: str, min_val: int, max_val: int) -> Tuple[bool, Optional[int]]:
    """Checks if numeric input stays within specified ranges."""
    cleaned = clean_numeric_input(text)
    if not cleaned.isdigit():
        return False, None
    
    value = int(cleaned)
    if min_val <= value <= max_val:
        return True, value
    return False, None


def validate_float(text: str, min_val: float, max_val: float) -> Tuple[bool, Optional[float]]:
    """Checks if float input stays within specified ranges."""
    cleaned = clean_numeric_input(text)
    try:
        value = float(cleaned)
        if min_val <= value <= max_val:
            return True, value
        return False, None
    except ValueError:
        return False, None


@lru_cache(maxsize=128)
def validate_time(text: str) -> Optional[str]:
    """Formats time and ensures it is a valid HH:MM."""
    match = re.match(
        r'^([0-1]?[0-9]|2[0-4])[\s\.\-:]([0-5][0-9])$', 
        text.strip()
    )
    if not match:
        return None
    
    hours, minutes = map(int, match.groups())
    
    if hours == 24 and minutes == 0:
        hours = 0
    
    if hours > 23 or minutes > 59:
        return None
    
    return f"{hours:02d}:{minutes:02d}"


def validate_text_input(text: str, max_length: int = 1000, min_length: int = 1) -> Tuple[bool, str]:
    """
    Validate and sanitize user text input.
    
    Args:
        text: Input text to validate
        max_length: Maximum allowed length
        min_length: Minimum required length
    
    Returns:
        Tuple of (is_valid, cleaned_text)
    """
    if not text or not isinstance(text, str):
        return False, ""
    
    cleaned = text.strip()
    
    if len(cleaned) < min_length:
        return False, ""
    
    if len(cleaned) > max_length:
        return False, cleaned[:max_length]
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    return True, cleaned


def calculate_sleep_duration(bedtime_str: str, wakeup_str: str) -> float:
    """
    Calculate sleep duration in hours, handling cross-midnight schedules.
    
    Args:
        bedtime_str: Time in HH:MM format (e.g., "23:00")
        wakeup_str: Time in HH:MM format (e.g., "07:00")
    
    Returns:
        Sleep duration in hours (float)
    """
    time_format = "%H:%M"
    
    bedtime = datetime.strptime(bedtime_str, time_format)
    wakeup = datetime.strptime(wakeup_str, time_format)
    
    # If wakeup is before bedtime, assume it's the next day
    if wakeup <= bedtime:
        wakeup += timedelta(days=1)
    
    duration = (wakeup - bedtime).total_seconds() / 3600
    return duration


def validate_sleep_schedule(bedtime: str, wakeuptime: str) -> Tuple[bool, Optional[str]]:
    """
    Validate sleep schedule durations.

    Args:
        bedtime: Time in HH:MM format (e.g., "23:00")
        wakeuptime: Time in HH:MM format (e.g., "07:00")
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        duration = calculate_sleep_duration(bedtime, wakeuptime)
        
        # Check minimum sleep
        if duration < MIN_SLEEP_HOURS:
            return False, f"⚠️ Sleep duration ({duration:.1f}h) is too short. Minimum {MIN_SLEEP_HOURS} hours recommended."
        
        # Check maximum sleep
        if duration > MAX_SLEEP_HOURS:
            return False, f"⚠️ Sleep duration ({duration:.1f}h) is too long. Maximum {MAX_SLEEP_HOURS} hours."
        
        return True, None
        
    except ValueError:
        return False, "⚠️ Invalid time format. Please use HH:MM."


def calculate_notification_defaults(wakeup_str: str, bedtime_str: str) -> list[str]:
    """
    Calculate default notification times based on wake-up and bedtime.

    Args:
        wakeup_str: Wake-up time in HH:MM format
        bedtime_str: Bedtime in HH:MM format
    
    Returns:
        List of 3 notification times [morning, day, evening]
    """
    time_format = "%H:%M"
    
    wakeup = datetime.strptime(wakeup_str, time_format)
    bedtime = datetime.strptime(bedtime_str, time_format)
    
    # Morning: 1 hour after wakeup
    morning_time = wakeup + timedelta(hours=NOTIFICATION_MORNING_OFFSET_HOURS)
    morning = morning_time.strftime(time_format)
    
    # Day: 7 hours after wakeup
    day_time = wakeup + timedelta(hours=NOTIFICATION_DAY_OFFSET_HOURS)
    day = day_time.strftime(time_format)
    
    # Evening: 2 hours before bedtime (handle previous day case)
    evening_time = bedtime + timedelta(hours=NOTIFICATION_EVENING_OFFSET_HOURS)
    
    # If evening notification would be before morning, adjust
    if evening_time < wakeup:
        evening_time += timedelta(days=1)
    
    evening = evening_time.strftime(time_format)
    
    return [morning, day, evening]


def detect_timezone_from_language(language_code: str) -> str:
    """Maps user's app language to a default timezone."""
    return LANGUAGE_TO_TIMEZONE.get(language_code, DEFAULT_TIMEZONE)


def validate_rating(value: int, min_val: int = 1, max_val: int = 5) -> bool:
    """
    Validate rating is within range.
    
    Args:
        value: Rating value
        min_val: Minimum allowed (default: 1)
        max_val: Maximum allowed (default: 5)
    
    Returns:
        True if valid
    """
    return min_val <= value <= max_val


def has_negation_before(text: str, keyword: str) -> bool:
    """
    Check if a keyword is negated in the text.
        
    Args:
        text: Text to analyze
        keyword: Keyword to check for negation
    
    Returns:
        True if keyword is negated
    """
    text_lower = text.lower()
    
    # Find keyword position
    keyword_pos = text_lower.find(keyword.lower())
    if keyword_pos == -1:
        return False
    
    # Check 3 words before for negation
    words_before = text_lower[:keyword_pos].split()[-3:]
    
    return any(neg in words_before for neg in NEGATION_WORDS)


# ============================================================================
# TIMEZONE VALIDATION (NEW - Fix #3)
# ============================================================================

def validate_timezone(timezone_str: str) -> Optional[str]:
    """
    Validate timezone string against pytz database.
    
    Args:
        timezone_str: Timezone string (e.g., "Europe/Kyiv", "UTC")
    
    Returns:
        Valid timezone string or None
    """
    if not timezone_str:
        return None
    
    # Clean input
    timezone_str = timezone_str.strip()
    
    # Common aliases for user-friendly input
    timezone_aliases = {
        'kyiv': 'Europe/Kyiv',
        'kiev': 'Europe/Kyiv',
        'ukraine': 'Europe/Kyiv',
        'moscow': 'Europe/Moscow',
        'russia': 'Europe/Moscow',
        'london': 'Europe/London',
        'uk': 'Europe/London',
        'paris': 'Europe/Paris',
        'france': 'Europe/Paris',
        'berlin': 'Europe/Berlin',
        'germany': 'Europe/Berlin',
        'warsaw': 'Europe/Warsaw',
        'poland': 'Europe/Poland',
        'new york': 'America/New_York',
        'ny': 'America/New_York',
        'los angeles': 'America/Los_Angeles',
        'la': 'America/Los_Angeles',
        'chicago': 'America/Chicago',
        'tokyo': 'Asia/Tokyo',
        'japan': 'Asia/Tokyo',
        'beijing': 'Asia/Shanghai',
        'china': 'Asia/Shanghai',
        'dubai': 'Asia/Dubai',
        'sydney': 'Australia/Sydney',
        'melbourne': 'Australia/Melbourne',
        'utc': 'UTC',
        'gmt': 'GMT',
    }
    
    # Check if it's an alias
    timezone_lower = timezone_str.lower()
    if timezone_lower in timezone_aliases:
        timezone_str = timezone_aliases[timezone_lower]
    
    # Validate against pytz
    try:
        pytz.timezone(timezone_str)
        return timezone_str
    except pytz.exceptions.UnknownTimeZoneError:
        return None


def get_common_timezones() -> list[str]:
    """
    Get list of common timezones for suggestions.
    
    Returns:
        List of common timezone strings
    """
    return [
        'UTC',
        'Europe/Kyiv',
        'Europe/Moscow',
        'Europe/London',
        'Europe/Paris',
        'Europe/Berlin',
        'Europe/Warsaw',
        'Europe/Rome',
        'Europe/Madrid',
        'America/New_York',
        'America/Chicago',
        'America/Los_Angeles',
        'Asia/Tokyo',
        'Asia/Shanghai',
        'Asia/Dubai',
        'Australia/Sydney',
    ]


def format_timezone_suggestions() -> str:
    """
    Format common timezones for display to user.
    
    Returns:
        Formatted HTML string with timezone examples
    """
    common = get_common_timezones()
    suggestions = '\n'.join([f"• <code>{tz}</code>" for tz in common[:8]])
    return f"<b>Common timezones:</b>\n{suggestions}\n\n<b>Or type city/country:</b> London, Berlin, Kyiv, Tokyo, etc."