# ============================================================================
# BUTTON TEXTS
# ============================================================================

BTN_BACK = "⬅️ Back"
BTN_CONTINUE = "➡️ Continue"
BTN_SKIP = "⏭ Skip"
BTN_CREATE_PROFILE = "Create Profile 🚀"
BTN_LATER = "Later"

# ============================================================================
# GENDER OPTIONS
# ============================================================================

GENDER_MALE = "Male"
GENDER_FEMALE = "Female"
GENDERS = [GENDER_MALE, GENDER_FEMALE]

# ============================================================================
# ACTIVITY LEVELS
# ============================================================================

ACTIVITY_LOW = "Low"
ACTIVITY_MEDIUM = "Medium"
ACTIVITY_HIGH = "High"
ACTIVITY_LEVELS = [ACTIVITY_LOW, ACTIVITY_MEDIUM, ACTIVITY_HIGH]

# ============================================================================
# VALIDATION RANGES
# ============================================================================

AGE_MIN = 11
AGE_MAX = 109

HEIGHT_MIN = 100
HEIGHT_MAX = 280

WEIGHT_MIN = 30
WEIGHT_MAX = 300

# Sleep validation
MIN_SLEEP_HOURS = 4
MAX_SLEEP_HOURS = 12

# ============================================================================
# HABITS
# ============================================================================

HABIT_WATER = "Water"
HABIT_ACTIVITY = "Activity"
HABIT_MEDITATION = "Meditation"
HABIT_MEDICATION = "Medication"
HABITS = [HABIT_WATER, HABIT_ACTIVITY, HABIT_MEDITATION, HABIT_MEDICATION]

# ============================================================================
# SCHEDULER CONSTANTS
# ============================================================================

PERIODS = ["morning", "day", "evening"]

REMINDER_MESSAGES = {
    "morning": (
        "🌅 <b>Good morning!</b>\n\n"
        "Time for your morning check-in. "
        "It only takes 2 minutes to track your sleep and set your day's intentions."
    ),
    "day": (
        "☀️ <b>Midday check!</b>\n\n"
        "How's your day going? "
        "Quick check-in to track your mood and energy levels."
    ),
    "evening": (
        "🌙 <b>Evening reflection time!</b>\n\n"
        "Let's wrap up your day. "
        "Reflect on what went well and what you learned today."
    )
}

DEFAULT_MESSAGE = "⏰ Time for your check-in!"

REMIND_LATER_INTERVAL = 15  # minutes
REMIND_LATER_MAX_COUNT = 2  # maximum number of "remind me later" clicks

# ============================================================================
# MESSAGES
# ============================================================================

MSG_USE_BUTTONS = "⚠️ Please use the buttons!"
MSG_PROFILE_EXISTS = "✅ You already have a profile!"
MSG_PROFILE_CREATED = "✅ <b>Profile created!</b>"
MSG_DB_ERROR = "❌ Error saving to database. Please try again or contact support."
MSG_REGISTRATION_CANCELLED = "Registration cancelled."
MSG_INVALID_AGE = f"⚠️ Please enter a valid age ({AGE_MIN}-{AGE_MAX}):"
MSG_INVALID_HEIGHT = f"⚠️ Enter valid height ({HEIGHT_MIN}-{HEIGHT_MAX} cm):"
MSG_INVALID_WEIGHT = f"⚠️ Enter valid weight ({WEIGHT_MIN}-{WEIGHT_MAX} kg):"
MSG_INVALID_TIME = "⚠️ Use format HH:MM (e.g., 23:30):"
MSG_INVALID_SLEEP_SCHEDULE = f"⚠️ Sleep duration must be between {MIN_SLEEP_HOURS}-{MAX_SLEEP_HOURS} hours. Please adjust your times."

# Error messages for users
MSG_ERROR_GENERIC = "❌ Something went wrong. Please try again in a moment."
MSG_ERROR_NETWORK = "📡 Connection issue. Please check your internet and try again."
MSG_ERROR_DATABASE = "💾 Database temporarily unavailable. Your data is safe, please retry."

# ============================================================================
# PROMPTS
# ============================================================================

PROMPT_GENDER = "Select your gender:"
PROMPT_AGE = "How old are you? (e.g., 25)"
PROMPT_HEIGHT = "Your height (e.g., 175 cm):"
PROMPT_WEIGHT = "Your weight (e.g., 70 kg):"
PROMPT_ACTIVITY = "Select your daily activity level: \nLow - mostly sitting,\nMedium - some walking,\nHigh - physically workouts"
PROMPT_BEDTIME = "What is your usual bedtime? (HH:MM)"
PROMPT_WAKEUP = "What is your usual wake-up time? (HH:MM)"
PROMPT_TIMEZONE_DETECTED = "🌍 Detected timezone: <b>{timezone}</b>\nIs this correct?"
PROMPT_TIMEZONE_MANUAL = "Enter your timezone (e.g., <code>Europe/Kyiv</code>):"
PROMPT_HABITS = "🛠 <b>Select habits to track:</b>\n(Toggle them, then press Continue)"
PROMPT_NOTIFICATIONS = "How should we set up your notifications?"

# ============================================================================
# TIMEZONE MAPPINGS
# ============================================================================

LANGUAGE_TO_TIMEZONE = {
    "uk": "Europe/Kyiv",
    "en": "UTC",
    "pl": "Europe/Warsaw",
    "de": "Europe/Berlin",
    "ru": "Europe/Moscow",
    "fr": "Europe/Paris",
    "es": "Europe/Madrid",
    "it": "Europe/Rome",
}

DEFAULT_TIMEZONE = "UTC"

# ============================================================================
# NOTIFICATION DEFAULTS
# ============================================================================

NOTIFICATION_MORNING_OFFSET_HOURS = 1
NOTIFICATION_DAY_OFFSET_HOURS = 7
NOTIFICATION_EVENING_OFFSET_HOURS = -2

# ============================================================================
# TAG CATEGORIES (CENTRALIZED - Issue #6)
# ============================================================================

TAG_KEYWORDS = {
    # Stress Sources
    'work_stress': [
        'work', 'job', 'boss', 'deadline', 'meeting', 'project', 'office',
        'colleague', 'presentation', 'client', 'overtime', 'workload'
    ],
    'relationship_stress': [
        'partner', 'spouse', 'family', 'argument', 'fight', 'conflict',
        'relationship', 'marriage', 'divorce', 'breakup', 'parents'
    ],
    'financial_stress': [
        'money', 'bills', 'debt', 'financial', 'budget', 'expensive',
        'afford', 'salary', 'payment', 'rent', 'mortgage', 'loan'
    ],
    'health_stress': [
        'sick', 'pain', 'health', 'doctor', 'hospital', 'illness',
        'injury', 'medication', 'headache', 'backache', 'anxiety'
    ],
    'time_pressure': [
        'rushed', 'hurry', 'late', 'busy', 'overwhelmed', 'too much',
        'no time', 'behind', 'deadline', 'pressure', 'stressed'
    ],
    
    # Positive Activities
    'exercise': [
        'gym', 'run', 'running', 'walk', 'walking', 'workout', 'exercise',
        'sport', 'yoga', 'fitness', 'training', 'jogging', 'swimming'
    ],
    'social_time': [
        'friends', 'social', 'party', 'gathering', 'hangout', 'visit',
        'dinner', 'lunch', 'coffee', 'chat', 'conversation', 'connection'
    ],
    'hobby_time': [
        'hobby', 'reading', 'book', 'music', 'playing', 'game', 'cooking',
        'painting', 'drawing', 'creative', 'fun', 'enjoyable'
    ],
    'meditation': [
        'meditate', 'meditation', 'mindfulness', 'breathing', 'calm',
        'relaxation', 'peaceful', 'zen', 'quiet time', 'reflection'
    ],
    'nature': [
        'nature', 'outdoor', 'park', 'forest', 'beach', 'hiking',
        'garden', 'outside', 'fresh air', 'sunshine', 'walk outside'
    ],
    
    # Sleep Issues
    'trouble_falling_asleep': [
        'can\'t sleep', 'couldn\'t sleep', 'insomnia', 'lying awake',
        'tossing', 'turning', 'mind racing', 'can\'t fall asleep'
    ],
    'waking_up_night': [
        'woke up', 'waking up', 'interrupted sleep', 'restless',
        'kept waking', 'multiple times', 'nightmare', 'disrupted'
    ],
    'not_enough_sleep': [
        'not enough sleep', 'lack of sleep', 'tired', 'exhausted',
        'fatigue', 'sleep deprived', 'only slept', 'few hours'
    ],
    
    # Mood Factors
    'achievement': [
        'achieved', 'accomplished', 'success', 'completed', 'finished',
        'proud', 'well done', 'great job', 'productive', 'progress'
    ],
    'disappointment': [
        'disappointed', 'failed', 'didn\'t work', 'upset', 'frustrated',
        'let down', 'didn\'t go well', 'expected', 'hoped'
    ],
    'conflict': [
        'argument', 'fight', 'disagreement', 'conflict', 'tension',
        'angry', 'frustrated with', 'argued', 'dispute'
    ],
    'lonely': [
        'lonely', 'alone', 'isolated', 'miss', 'missing', 'solitary',
        'no one', 'by myself', 'wished someone', 'loneliness'
    ],
    'overwhelmed': [
        'overwhelmed', 'too much', 'can\'t handle', 'drowning',
        'swamped', 'buried', 'overloaded', 'can\'t cope'
    ],
}

# Tag categories for filtering
TAG_CATEGORIES = {
    'stressor': ['work_stress', 'relationship_stress', 'financial_stress', 
                 'health_stress', 'time_pressure'],
    'activity': ['exercise', 'social_time', 'hobby_time', 'meditation', 'nature'],
    'sleep': ['trouble_falling_asleep', 'waking_up_night', 'not_enough_sleep'],
    'mood': ['achievement', 'disappointment', 'conflict', 'lonely', 'overwhelmed']
}

# Sentiment keywords (improved - Issue #14)
POSITIVE_KEYWORDS = [
    'good', 'great', 'excellent', 'happy', 'joy', 'wonderful', 'amazing',
    'love', 'beautiful', 'peaceful', 'relaxed', 'proud', 'grateful',
    'blessed', 'lucky', 'excited', 'hopeful', 'optimistic', 'satisfied',
    'pleased', 'delighted', 'fantastic', 'perfect', 'better', 'improved'
]

NEGATIVE_KEYWORDS = [
    'bad', 'terrible', 'awful', 'sad', 'depressed', 'anxious', 'worried',
    'stressed', 'angry', 'frustrated', 'upset', 'disappointed', 'tired',
    'exhausted', 'overwhelmed', 'hopeless', 'miserable', 'unhappy', 'worse',
    'horrible', 'difficult', 'struggling', 'painful', 'hard'
]

# Negation words for improved sentiment analysis (Issue #14)
NEGATION_WORDS = ['not', 'no', 'never', 'none', 'nobody', 'nothing', 'neither', 
                  'nowhere', 'hardly', 'barely', 'scarcely', "don't", "doesn't", 
                  "didn't", "won't", "wouldn't", "shouldn't", "can't", "cannot"]

# ============================================================================
# CACHING SETTINGS (Issue #15)
# ============================================================================

CACHE_WEEKLY_STATS_TTL = 3600  # 1 hour
CACHE_TAG_EXTRACTION_TTL = 1800  # 30 minutes
CACHE_USER_PROFILE_TTL = 600  # 10 minutes

# ============================================================================
# LOGGING SETTINGS (Issue #19)
# ============================================================================

LOG_LEVEL_DEFAULT = "INFO"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_FILE_BACKUP_COUNT = 5