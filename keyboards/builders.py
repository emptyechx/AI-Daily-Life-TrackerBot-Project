from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import (
    KeyboardButton,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove
)

from utils.constants import (
    BTN_BACK,
    BTN_CONTINUE,
    BTN_SKIP,
    BTN_CREATE_PROFILE,
    BTN_LATER,
    GENDERS,
    ACTIVITY_LEVELS,
    HABITS,
)


# ============================================================================
# REPLY KEYBOARDS (Physical keyboard buttons)
# ============================================================================

def create_back_keyboard() -> ReplyKeyboardMarkup:
    """Creates a standard reply keyboard with a single 'Back' button."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=BTN_BACK))
    return builder.as_markup(resize_keyboard=True)


def create_skip_keyboard() -> ReplyKeyboardMarkup:
    """Creates a reply keyboard with a 'Skip' button for optional steps."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=BTN_SKIP))
    return builder.as_markup(resize_keyboard=True)


def create_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Creates the initial welcome keyboard for profile creation or deferral."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=BTN_CREATE_PROFILE),
        KeyboardButton(text=BTN_LATER)
    )
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def create_gender_keyboard() -> ReplyKeyboardMarkup:
    """Generates a gender selection keyboard from a list with a back button."""
    builder = ReplyKeyboardBuilder()
    for gender in GENDERS:
        builder.add(KeyboardButton(text=gender))
    builder.row(KeyboardButton(text=BTN_BACK))
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)


def create_activity_keyboard() -> ReplyKeyboardMarkup:
    """Generates an activity level selection keyboard with a 3-column layout."""
    builder = ReplyKeyboardBuilder()
    for level in ACTIVITY_LEVELS:
        builder.add(KeyboardButton(text=level))
    builder.row(KeyboardButton(text=BTN_BACK))
    builder.adjust(3, 1)
    return builder.as_markup(resize_keyboard=True)


def remove_keyboard() -> ReplyKeyboardRemove:
    """Removes the current reply keyboard from the user's interface."""
    return ReplyKeyboardRemove()


# ============================================================================
# INLINE KEYBOARDS (Buttons below messages)
# ============================================================================

def create_habits_keyboard(selected_habits: list[str]) -> InlineKeyboardMarkup:
    """Creates an inline toggle-style keyboard for selecting multiple habits."""
    builder = InlineKeyboardBuilder()

    for habit in HABITS:
        status = "✅" if habit in selected_habits else "⬜"
        builder.button(
            text=f"{status} {habit}",
            callback_data=f"toggle_{habit}"
        )

    # Arrange habit buttons into 2 columns per row
    builder.adjust(2)

    # Final row with Continue and Back
    builder.row(
        InlineKeyboardButton(text=BTN_CONTINUE, callback_data="continue"),
        InlineKeyboardButton(text=BTN_BACK, callback_data="go_back"),
    )

    return builder.as_markup()


def create_edit_habits_keyboard(selected_habits: list[str]) -> InlineKeyboardMarkup:
    """Creates a toggleable list of habits specifically for the profile editing mode."""
    builder = InlineKeyboardBuilder()

    for habit in HABITS:
        status = "✅" if habit in selected_habits else "⬜"
        builder.button(
            text=f"{status} {habit}",
            callback_data=f"toggle_habit_{habit}"  # Different callback for edit mode
        )

    builder.adjust(2)

    # Final row with Save and Back
    builder.row(
        InlineKeyboardButton(text="✅ Save Habits", callback_data="save_habits_edit"),
        InlineKeyboardButton(text=BTN_BACK, callback_data="cancel_habits_edit"),
    )

    return builder.as_markup()


def create_timezone_keyboard() -> InlineKeyboardMarkup:
    """Creates an inline keyboard to confirm or modify the detected timezone."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Correct", callback_data="timezone_correct")
    builder.button(text="🔄 Change", callback_data="timezone_change")
    builder.adjust(2)
    return builder.as_markup()


def create_notifications_choice_keyboard() -> InlineKeyboardMarkup:
    """Creates an inline keyboard for choosing between automatic and manual notification setup."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Default (Auto)", callback_data="notify_default")
    builder.button(text="✏️ Custom setup", callback_data="notify_custom")
    builder.adjust(1)
    return builder.as_markup()


def create_final_confirm_keyboard() -> InlineKeyboardMarkup:
    """Creates an inline keyboard for the final step of profile creation to save or reset data."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Save Profile", callback_data="save_profile")
    builder.button(text="⬅️ Start over", callback_data="start_over")
    builder.adjust(1)
    return builder.as_markup()


def create_edit_profile_keyboard() -> InlineKeyboardMarkup:
    """Creates a comprehensive settings menu for modifying specific user profile fields."""
    builder = InlineKeyboardBuilder()

    fields = [
        ("👤 First Name", "edit_first_name"),
        ("🚻 Gender", "edit_gender"),
        ("🎂 Age", "edit_age"),
        ("⚖️ Weight", "edit_weight"),
        ("📏 Height", "edit_height"),
        ("🏃 Activity Level", "edit_activity_level"),
        ("🌙 Usual Bedtime", "edit_bedtime_usual"),
        ("☀️ Usual Wake-up Time", "edit_wakeuptime_usual"),
        ("🛠 Habits to Track", "edit_habits"),
        ("📲 Notification Times", "edit_notification_times"),
        ("🌍 Timezone", "edit_timezone")
    ]

    for text, callback in fields:
        builder.button(text=text, callback_data=callback)

    builder.button(text="✅ Finish Editing", callback_data="edit_finish_editing")
    builder.adjust(1)
    return builder.as_markup()


# ============================================================================
# CHECK-IN KEYBOARDS
# ============================================================================

def create_rating_keyboard() -> InlineKeyboardMarkup:
    """Creates a horizontal 1-5 rating scale using inline buttons."""
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.button(text=str(i), callback_data=f"rate_{i}")
    builder.adjust(5)
    return builder.as_markup()


def create_satisfaction_keyboard() -> InlineKeyboardMarkup:
    """Creates a simple satisfaction feedback keyboard with two emotional states."""
    builder = InlineKeyboardBuilder()
    builder.button(text="😞 Not satisfied", callback_data="satisfaction_bad")
    builder.button(text="😊 Satisfied", callback_data="satisfaction_good")
    builder.adjust(1)
    return builder.as_markup()


def create_wakeup_keyboard() -> InlineKeyboardMarkup:
    """Creates an inline keyboard for tracking wake-up punctuality."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ On time", callback_data="wakeup_ontime")
    builder.button(text="⏰ Late", callback_data="wakeup_late")
    builder.adjust(1)
    return builder.as_markup()


def create_checkin_keyboard(period: str, remind_count: int = 0) -> InlineKeyboardMarkup:
    """
    Creates a contextual entry point for check-ins with dynamic buttons.
    
    Args:
        period: Check-in period ('morning', 'day', 'evening')
        remind_count: Number of times user clicked "Remind later" (0-2)
    
    Returns:
        Inline keyboard with appropriate options
    """
    builder = InlineKeyboardBuilder()
    
    # Start button
    if period == "morning":
        builder.button(text="🌅 Start Morning Check-in", callback_data="start_morning")
    elif period in ["afternoon", "day"]:
        builder.button(text="☀️ Start Day Check-in", callback_data="start_day")
    elif period == "evening":
        builder.button(text="🌙 Start Evening Check-in", callback_data="start_evening")
    
    # Show "Remind later" only if not used 2+ times
    if remind_count < 2:
        builder.button(text="⏰ Remind me later (15 min)", callback_data=f"remind_later_{period}")
    
    # Always show skip option
    builder.button(text="⏭ Skip this check-in", callback_data=f"skip_checkin_{period}")
    
    # Layout: all buttons in separate rows for clarity
    builder.adjust(1)
    return builder.as_markup()