import pytest
from datetime import datetime
from utils.validators import (
    escape_html,
    clean_numeric_input,
    validate_integer,
    validate_float,
    validate_time,
    validate_text_input,
    calculate_sleep_duration,
    validate_sleep_schedule,
    calculate_notification_defaults,
    detect_timezone_from_language,
    validate_rating,
    has_negation_before,
    validate_timezone,
    get_common_timezones,
)


# ============================================================================
# HTML ESCAPING TESTS
# ============================================================================

def test_escape_html():
    """Test HTML special character escaping."""
    assert escape_html("<b>test</b>") == "&lt;b&gt;test&lt;/b&gt;"
    assert escape_html("Hello & goodbye") == "Hello &amp; goodbye"
    assert escape_html("Quote: \"text\"") == "Quote: &quot;text&quot;"
    assert escape_html("Normal text") == "Normal text"


# ============================================================================
# NUMERIC INPUT TESTS
# ============================================================================

def test_clean_numeric_input():
    """Test numeric input cleaning."""
    assert clean_numeric_input("123") == "123"
    assert clean_numeric_input("12.5") == "12.5"
    assert clean_numeric_input("12,5") == "12.5"  # Comma to dot
    assert clean_numeric_input("abc123def") == "123"
    assert clean_numeric_input("12.5kg") == "12.5"


def test_validate_integer():
    """Test integer validation with ranges."""
    # Valid cases
    assert validate_integer("25", 18, 100) == (True, 25)
    assert validate_integer("18", 18, 100) == (True, 18)
    assert validate_integer("100", 18, 100) == (True, 100)
    
    # Invalid cases
    assert validate_integer("17", 18, 100) == (False, None)
    assert validate_integer("101", 18, 100) == (False, None)
    assert validate_integer("abc", 18, 100) == (False, None)
    assert validate_integer("12.5", 18, 100) == (False, None)


def test_validate_float():
    """Test float validation with ranges."""
    # Valid cases
    assert validate_float("70.5", 30.0, 300.0) == (True, 70.5)
    assert validate_float("30", 30.0, 300.0) == (True, 30.0)
    assert validate_float("175,5", 100.0, 250.0) == (True, 175.5)
    
    # Invalid cases
    assert validate_float("29.9", 30.0, 300.0) == (False, None)
    assert validate_float("300.1", 30.0, 300.0) == (False, None)
    assert validate_float("abc", 30.0, 300.0) == (False, None)


# ============================================================================
# TIME VALIDATION TESTS
# ============================================================================

def test_validate_time():
    """Test time format validation."""
    # Valid formats
    assert validate_time("23:30") == "23:30"
    assert validate_time("08:00") == "08:00"
    assert validate_time("0:00") == "00:00"
    assert validate_time("9:5") == "09:05"
    assert validate_time("23.30") == "23:30"
    assert validate_time("23-30") == "23:30"
    assert validate_time("23:30") == "23:30"
    
    # Edge cases
    assert validate_time("24:00") == "00:00"  # Midnight conversion
    assert validate_time("00:00") == "00:00"
    
    # Invalid formats
    assert validate_time("25:00") is None
    assert validate_time("23:60") is None
    assert validate_time("abc") is None
    assert validate_time("12") is None
    assert validate_time("") is None


# ============================================================================
# TEXT INPUT TESTS
# ============================================================================

def test_validate_text_input():
    """Test text input validation and sanitization."""
    # Valid cases
    assert validate_text_input("Hello world", max_length=100) == (True, "Hello world")
    assert validate_text_input("  Spaces  ", max_length=100) == (True, "Spaces")
    
    # Multiple spaces cleanup
    is_valid, cleaned = validate_text_input("Too   many    spaces", max_length=100)
    assert is_valid is True
    assert cleaned == "Too many spaces"
    
    # Too long
    long_text = "a" * 1001
    is_valid, cleaned = validate_text_input(long_text, max_length=1000)
    assert is_valid is False
    assert len(cleaned) == 1000
    
    # Too short
    assert validate_text_input("", min_length=1) == (False, "")
    assert validate_text_input("   ", min_length=1) == (False, "")
    
    # Invalid type
    assert validate_text_input(None) == (False, "")
    assert validate_text_input(123) == (False, "")


# ============================================================================
# SLEEP SCHEDULE TESTS
# ============================================================================

def test_calculate_sleep_duration():
    """Test sleep duration calculation."""
    # Normal sleep (same day)
    assert calculate_sleep_duration("23:00", "07:00") == 8.0
    
    # Short sleep
    assert calculate_sleep_duration("02:00", "06:00") == 4.0
    
    # Long sleep
    assert calculate_sleep_duration("22:00", "10:00") == 12.0
    
    # Midnight handling
    assert calculate_sleep_duration("00:00", "08:00") == 8.0
    assert calculate_sleep_duration("23:59", "00:01") == pytest.approx(0.033, rel=0.1)


def test_validate_sleep_schedule():
    """Test sleep schedule validation."""
    # Valid schedules
    assert validate_sleep_schedule("23:00", "07:00") == (True, None)
    assert validate_sleep_schedule("22:00", "06:00") == (True, None)
    
    # Too short
    is_valid, error = validate_sleep_schedule("02:00", "05:00")
    assert is_valid is False
    assert "too short" in error.lower()
    
    # Too long
    is_valid, error = validate_sleep_schedule("20:00", "10:00")
    assert is_valid is False
    assert "too long" in error.lower()


def test_calculate_notification_defaults():
    """Test default notification time calculation."""
    times = calculate_notification_defaults("07:00", "23:00")
    
    assert len(times) == 3
    assert times[0] == "08:00"  # 1 hour after wakeup
    assert times[1] == "14:00"  # 7 hours after wakeup
    assert times[2] == "21:00"  # 2 hours before bedtime
    
    # Edge case: late sleeper
    times = calculate_notification_defaults("10:00", "02:00")
    assert times[0] == "11:00"
    assert times[1] == "17:00"


# ============================================================================
# TIMEZONE TESTS
# ============================================================================

def test_detect_timezone_from_language():
    """Test timezone detection from language code."""
    assert detect_timezone_from_language("uk") == "Europe/Kyiv"
    assert detect_timezone_from_language("en") == "UTC"
    assert detect_timezone_from_language("de") == "Europe/Berlin"
    assert detect_timezone_from_language("unknown") == "UTC"  # Default


def test_validate_timezone():
    """Test timezone validation."""
    # Valid timezones
    assert validate_timezone("Europe/Kyiv") == "Europe/Kyiv"
    assert validate_timezone("UTC") == "UTC"
    assert validate_timezone("America/New_York") == "America/New_York"
    
    # Aliases
    assert validate_timezone("kyiv") == "Europe/Kyiv"
    assert validate_timezone("berlin") == "Europe/Berlin"
    assert validate_timezone("london") == "Europe/London"
    
    # Invalid
    assert validate_timezone("Invalid/Timezone") is None
    assert validate_timezone("") is None
    assert validate_timezone("Mars/Colony") is None


def test_get_common_timezones():
    """Test common timezones list."""
    timezones = get_common_timezones()
    
    assert isinstance(timezones, list)
    assert len(timezones) > 0
    assert "UTC" in timezones
    assert "Europe/Kyiv" in timezones
    assert "America/New_York" in timezones


# ============================================================================
# RATING VALIDATION TESTS
# ============================================================================

def test_validate_rating():
    """Test rating validation."""
    # Valid ratings
    assert validate_rating(1) is True
    assert validate_rating(3) is True
    assert validate_rating(5) is True
    
    # Invalid ratings
    assert validate_rating(0) is False
    assert validate_rating(6) is False
    assert validate_rating(-1) is False


# ============================================================================
# SENTIMENT ANALYSIS TESTS
# ============================================================================

def test_has_negation_before():
    """Test negation detection."""
    # Negation present
    assert has_negation_before("I am not happy", "happy") is True
    assert has_negation_before("never felt good", "good") is True
    assert has_negation_before("I don't feel bad", "bad") is True
    
    # No negation
    assert has_negation_before("I am happy", "happy") is False
    assert has_negation_before("feeling good", "good") is False
    
    # Keyword not found
    assert has_negation_before("I am happy", "sad") is False


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================

def test_validate_time_edge_cases():
    """Test time validation edge cases."""
    # Whitespace handling
    assert validate_time("  23:30  ") == "23:30"
    
    # Single digit hours/minutes
    assert validate_time("9:05") == "09:05"
    assert validate_time("23:5") == "23:05"


def test_validate_integer_edge_cases():
    """Test integer validation edge cases."""
    # Boundary values
    assert validate_integer("18", 18, 18) == (True, 18)
    
    # Negative numbers
    assert validate_integer("-5", -10, 10) == (True, -5)
    
    # Empty string
    assert validate_integer("", 0, 100) == (False, None)


def test_validate_text_input_unicode():
    """Test text validation with Unicode characters."""
    # Emoji
    is_valid, cleaned = validate_text_input("Hello 👋 World", max_length=100)
    assert is_valid is True
    assert "👋" in cleaned
    
    # Other languages
    is_valid, cleaned = validate_text_input("Привіт світ", max_length=100)
    assert is_valid is True
    assert cleaned == "Привіт світ"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_full_registration_flow():
    """Test complete validation flow for registration."""
    # Age
    is_valid, age = validate_integer("25", 11, 109)
    assert is_valid and age == 25
    
    # Height
    is_valid, height = validate_float("175.5", 100.0, 280.0)
    assert is_valid and height == 175.5
    
    # Weight
    is_valid, weight = validate_float("70", 30.0, 300.0)
    assert is_valid and weight == 70.0
    
    # Sleep times
    bedtime = validate_time("23:00")
    wakeup = validate_time("07:00")
    assert bedtime and wakeup
    
    # Sleep schedule
    is_valid, error = validate_sleep_schedule(bedtime, wakeup)
    assert is_valid
    
    # Notification times
    times = calculate_notification_defaults(wakeup, bedtime)
    assert len(times) == 3
    
    # Timezone
    tz = validate_timezone("Europe/Kyiv")
    assert tz == "Europe/Kyiv"


# ============================================================================
# PERFORMANCE TESTS (Optional)
# ============================================================================

@pytest.mark.parametrize("time_str", [
    "00:00", "06:30", "12:00", "18:45", "23:59"
])
def test_validate_time_performance(time_str):
    """Test time validation with multiple inputs."""
    result = validate_time(time_str)
    assert result is not None


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def sample_profile_data():
    """Sample profile data for testing."""
    return {
        "age": 25,
        "height": 175.0,
        "weight": 70.0,
        "bedtime_usual": "23:00",
        "wakeuptime_usual": "07:00",
        "timezone": "Europe/Kyiv",
    }


def test_with_fixture(sample_profile_data):
    """Test using fixture."""
    assert validate_integer(str(sample_profile_data["age"]), 11, 109)[0]
    assert validate_time(sample_profile_data["bedtime_usual"]) is not None