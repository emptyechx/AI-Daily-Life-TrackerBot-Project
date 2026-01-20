"""Registration flow handlers - COMPLETE VERSION with visible feedback and working back buttons"""

import logging
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from handlers.states import Registration
from keyboards.builders import (
    create_gender_keyboard,
    create_activity_keyboard,
    create_back_keyboard,
    create_habits_keyboard,
    create_notifications_choice_keyboard,
    create_final_confirm_keyboard,
    create_main_menu_keyboard,
    create_timezone_keyboard,
    remove_keyboard,
)
from database.supabase_db import create_profile, get_user_profile
from scheduler import schedule_user_notifications
from utils.validators import (
    escape_html,
    validate_integer,
    validate_float,
    validate_time,
    calculate_notification_defaults,
    detect_timezone_from_language,
    validate_sleep_schedule,
    validate_timezone,
    format_timezone_suggestions,
)
from utils.constants import (
    BTN_BACK,
    BTN_CREATE_PROFILE,
    GENDERS,
    ACTIVITY_LEVELS,
    AGE_MIN,
    AGE_MAX,
    HEIGHT_MIN,
    HEIGHT_MAX,
    WEIGHT_MIN,
    WEIGHT_MAX,
    MSG_PROFILE_EXISTS,
    MSG_DB_ERROR,
    MSG_REGISTRATION_CANCELLED,
    MSG_INVALID_AGE,
    MSG_INVALID_HEIGHT,
    MSG_INVALID_WEIGHT,
    MSG_INVALID_TIME,
    PROMPT_GENDER,
    PROMPT_AGE,
    PROMPT_HEIGHT,
    PROMPT_WEIGHT,
    PROMPT_ACTIVITY,
    PROMPT_BEDTIME,
    PROMPT_WAKEUP,
    PROMPT_TIMEZONE_DETECTED,
    PROMPT_TIMEZONE_MANUAL,
    PROMPT_HABITS,
    PROMPT_NOTIFICATIONS,
)
from utils.navigation import handle_back_navigation, validate_button_choice

router = Router()
logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTION
# ============================================================================

async def disable_old_message_buttons(message: types.Message):
    """Remove inline keyboard from old message to prevent reuse."""
    try:
        await message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


# ============================================================================
# REGISTRATION START
# ============================================================================

@router.message(F.text == BTN_CREATE_PROFILE)
async def start_registration(message: types.Message, state: FSMContext) -> None:
    """Start registration process."""
    existing_profile = await get_user_profile(message.from_user.id)
    if existing_profile:
        return await message.answer(
            MSG_PROFILE_EXISTS, 
            reply_markup=create_main_menu_keyboard()
        )
    
    await state.set_state(Registration.gender)
    await message.answer(
        f"Let's get to know you, <b>{message.from_user.first_name}</b>! "
        f"This data helps AI personalize your experience.",
        parse_mode=ParseMode.HTML
    )
    await message.answer(PROMPT_GENDER, reply_markup=create_gender_keyboard())


# ============================================================================
# BASIC INFO (Gender, Age, Height, Weight, Activity)
# ============================================================================

@router.message(Registration.gender)
async def process_gender(message: types.Message, state: FSMContext) -> None:
    """Process gender selection."""
    if message.text == BTN_BACK:
        await state.clear()
        return await message.answer(
            MSG_REGISTRATION_CANCELLED,
            reply_markup=create_main_menu_keyboard()
        )
    
    selected_gender = await validate_button_choice(message, GENDERS)
    if not selected_gender:
        return
    
    await state.update_data(gender=selected_gender)
    await state.set_state(Registration.age)
    
    await message.answer(f"✅ {selected_gender}", reply_markup=remove_keyboard())
    await message.answer(PROMPT_AGE, reply_markup=create_back_keyboard())


@router.message(Registration.age)
async def process_age(message: types.Message, state: FSMContext) -> None:
    """Process age input."""
    if await handle_back_navigation(
        message, state,
        Registration.gender,
        PROMPT_GENDER,
        create_gender_keyboard
    ):
        return
    
    is_valid, age = validate_integer(message.text, AGE_MIN, AGE_MAX)
    if not is_valid:
        return await message.answer(MSG_INVALID_AGE)
    
    await state.update_data(age=age)
    await state.set_state(Registration.height)
    await message.answer(PROMPT_HEIGHT, reply_markup=create_back_keyboard())


@router.message(Registration.height)
async def process_height(message: types.Message, state: FSMContext) -> None:
    """Process height input."""
    if await handle_back_navigation(
        message, state,
        Registration.age,
        PROMPT_AGE,
        create_back_keyboard
    ):
        return
    
    is_valid, height = validate_float(message.text, HEIGHT_MIN, HEIGHT_MAX)
    if not is_valid:
        return await message.answer(MSG_INVALID_HEIGHT)
    
    await state.update_data(height=height)
    await state.set_state(Registration.weight)
    await message.answer(PROMPT_WEIGHT, reply_markup=create_back_keyboard())


@router.message(Registration.weight)
async def process_weight(message: types.Message, state: FSMContext) -> None:
    """Process weight input."""
    if await handle_back_navigation(
        message, state,
        Registration.height,
        PROMPT_HEIGHT,
        create_back_keyboard
    ):
        return
    
    is_valid, weight = validate_float(message.text, WEIGHT_MIN, WEIGHT_MAX)
    if not is_valid:
        return await message.answer(MSG_INVALID_WEIGHT)
    
    await state.update_data(weight=weight)
    await state.set_state(Registration.activity_level)
    await message.answer(PROMPT_ACTIVITY, reply_markup=create_activity_keyboard())


@router.message(Registration.activity_level)
async def process_activity(message: types.Message, state: FSMContext) -> None:
    """Process activity level selection."""
    if await handle_back_navigation(
        message, state,
        Registration.weight,
        PROMPT_WEIGHT,
        create_back_keyboard
    ):
        return
    
    selected_activity = await validate_button_choice(message, ACTIVITY_LEVELS)
    if not selected_activity:
        return
    
    await state.update_data(activity_level=selected_activity)
    await state.set_state(Registration.bedtime_usual)
    
    await message.answer(f"✅ {selected_activity}", reply_markup=remove_keyboard())
    await message.answer(PROMPT_BEDTIME, reply_markup=create_back_keyboard())


# ============================================================================
# SLEEP SCHEDULE
# ============================================================================

@router.message(Registration.bedtime_usual)
async def process_bedtime(message: types.Message, state: FSMContext) -> None:
    """Process bedtime input."""
    if await handle_back_navigation(
        message, state,
        Registration.activity_level,
        PROMPT_ACTIVITY,
        create_activity_keyboard
    ):
        return
    
    time = validate_time(message.text)
    if not time:
        return await message.answer(MSG_INVALID_TIME)
    
    await state.update_data(bedtime_usual=time)
    await state.set_state(Registration.wakeuptime_usual)
    await message.answer(PROMPT_WAKEUP, reply_markup=create_back_keyboard())


@router.message(Registration.wakeuptime_usual)
async def process_wakeup(message: types.Message, state: FSMContext) -> None:
    """Process wake-up time input with validation."""
    if await handle_back_navigation(
        message, state,
        Registration.bedtime_usual,
        PROMPT_BEDTIME,
        create_back_keyboard
    ):
        return
    
    time = validate_time(message.text)
    if not time:
        return await message.answer(MSG_INVALID_TIME)
    
    # Validate sleep schedule early
    data = await state.get_data()
    bedtime = data.get('bedtime_usual')
    
    if bedtime:
        is_valid, error_msg = validate_sleep_schedule(bedtime, time)
        if not is_valid:
            return await message.answer(
                error_msg + "\nPlease enter a valid time:",
                reply_markup=create_back_keyboard()
            )
    
    await state.update_data(wakeuptime_usual=time)
    await state.set_state(Registration.timezone)
    
    # Detect timezone from user's language
    detected_tz = detect_timezone_from_language(message.from_user.language_code)
    await state.update_data(detected_timezone=detected_tz)
    
    await message.answer(
        PROMPT_TIMEZONE_DETECTED.format(timezone=detected_tz),
        reply_markup=create_timezone_keyboard(),
        parse_mode=ParseMode.HTML
    )


# ============================================================================
# TIMEZONE SELECTION
# ============================================================================

@router.message(Registration.timezone, F.text == BTN_BACK)
async def back_from_timezone_message(message: types.Message, state: FSMContext) -> None:
    """Handle back button from timezone state (regular message)."""
    await state.set_state(Registration.wakeuptime_usual)
    await message.answer(PROMPT_WAKEUP, reply_markup=create_back_keyboard())


@router.callback_query(F.data == "timezone_correct")
async def timezone_correct(callback: types.CallbackQuery, state: FSMContext) -> None:
    """User confirmed detected timezone."""
    current_state = await state.get_state()
    if current_state != Registration.timezone:
        await callback.answer("⚠️ This action is no longer available.", show_alert=True)
        return
    
    data = await state.get_data()
    detected_tz = data['detected_timezone']
    await state.update_data(timezone=detected_tz)
    await state.set_state(Registration.habit_tracking)
    
    await disable_old_message_buttons(callback.message)
    
    # Show visible confirmation (clean format like gender)
    await callback.message.answer(f"✅ {detected_tz}", reply_markup=remove_keyboard())
    
    # Then show next step
    await callback.message.answer(
        PROMPT_HABITS,
        reply_markup=create_habits_keyboard([]),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "timezone_change")
async def timezone_change(callback: types.CallbackQuery, state: FSMContext) -> None:
    """User wants to enter timezone manually."""
    current_state = await state.get_state()
    if current_state != Registration.timezone:
        await callback.answer("⚠️ This action is no longer available.", show_alert=True)
        return
    
    await state.set_state(Registration.timezone_manual)
    
    await disable_old_message_buttons(callback.message)
    
    await callback.message.answer(
        PROMPT_TIMEZONE_MANUAL,
        reply_markup=create_back_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.message(Registration.timezone_manual)
async def process_timezone_manual(message: types.Message, state: FSMContext) -> None:
    """Process manually entered timezone with validation."""
    if message.text == BTN_BACK:
        await state.set_state(Registration.timezone)
        data = await state.get_data()
        detected_tz = data.get('detected_timezone', 'UTC')
        return await message.answer(
            PROMPT_TIMEZONE_DETECTED.format(timezone=detected_tz),
            reply_markup=create_timezone_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    user_tz = message.text.strip()
    validated_tz = validate_timezone(user_tz)
    
    if not validated_tz:
        suggestions = format_timezone_suggestions()
        return await message.answer(
            f"⚠️ Invalid timezone: <code>{user_tz}</code>\n\n{suggestions}",
            reply_markup=create_back_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    # Valid timezone
    await state.update_data(timezone=validated_tz)
    await state.set_state(Registration.habit_tracking)
    
    # Show confirmation (clean format like gender)
    await message.answer(f"✅ {validated_tz}", reply_markup=remove_keyboard())
    
    # Then show next step
    await message.answer(
        PROMPT_HABITS,
        reply_markup=create_habits_keyboard([]),
        parse_mode=ParseMode.HTML
    )


# ============================================================================
# HABITS SELECTION
# ============================================================================

@router.callback_query(F.data == "go_back", Registration.habit_tracking)
async def process_inline_back(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Handle back button from habits selection."""
    current_state = await state.get_state()
    if current_state != Registration.habit_tracking:
        await callback.answer("⚠️ This action is no longer available.", show_alert=True)
        return
    
    await state.set_state(Registration.timezone)
    data = await state.get_data()
    detected_tz = data.get('detected_timezone', 'UTC')
    
    await disable_old_message_buttons(callback.message)
    
    await callback.message.answer(
        PROMPT_TIMEZONE_DETECTED.format(timezone=detected_tz),
        reply_markup=create_timezone_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("toggle_") & ~F.data.startswith("toggle_habit_"),
    Registration.habit_tracking
)
async def toggle_habit(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Toggle habit selection."""
    current_state = await state.get_state()
    if current_state != Registration.habit_tracking:
        await callback.answer("⚠️ This action is no longer available.", show_alert=True)
        return
    
    habit = callback.data.split("_", 1)[1]
    data = await state.get_data()
    selected = data.get("selected_habits", [])
    
    # Determine action and show feedback
    if habit in selected:
        selected.remove(habit)
        await callback.answer(f"❌ {habit} removed", show_alert=False)
    else:
        selected.append(habit)
        await callback.answer(f"✅ {habit} added", show_alert=False)
    
    await state.update_data(selected_habits=selected)
    
    # Update keyboard
    try:
        await callback.message.edit_reply_markup(
            reply_markup=create_habits_keyboard(selected)
        )
    except Exception:
        pass


@router.callback_query(F.data == "continue", Registration.habit_tracking)
async def habits_done(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Finish habits selection and move to notifications."""
    current_state = await state.get_state()
    if current_state != Registration.habit_tracking:
        await callback.answer("⚠️ This action is no longer available.", show_alert=True)
        return
    
    await state.set_state(Registration.notification_setup)
    
    await disable_old_message_buttons(callback.message)
    
    # Show what was selected
    data = await state.get_data()
    selected_habits = data.get("selected_habits", [])
    
    if selected_habits:
        habits_display = "\n".join([f"  • {habit}" for habit in selected_habits])
        await callback.message.answer(
            f"✅ <b>Habits selected:</b>\n{habits_display}",
            parse_mode=ParseMode.HTML,
            reply_markup=remove_keyboard()
        )
    else:
        await callback.message.answer(
            "✅ <b>No habits selected</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=remove_keyboard()
        )
    
    # Then show next step
    await callback.message.answer(
        PROMPT_NOTIFICATIONS,
        reply_markup=create_notifications_choice_keyboard()
    )
    await callback.answer()


# ============================================================================
# NOTIFICATION SETUP
# ============================================================================

@router.callback_query(F.data == "notify_default", Registration.notification_setup)
async def notify_default(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Use default notification times."""
    current_state = await state.get_state()
    if current_state != Registration.notification_setup:
        await callback.answer("⚠️ This action is no longer available.", show_alert=True)
        return
    
    data = await state.get_data()
    
    if 'wakeuptime_usual' not in data or 'bedtime_usual' not in data:
        await callback.answer("⚠️ Missing profile data. Please try again.", show_alert=True)
        return
    
    times = calculate_notification_defaults(
        data['wakeuptime_usual'],
        data['bedtime_usual']
    )
    await state.update_data(
        use_default_notifications=True,
        notification_times=times
    )
    
    await disable_old_message_buttons(callback.message)
    
    # Show visible confirmation of default times
    await callback.message.answer(
        f"✅ <b>Default notifications set:</b>\n"
        f"🌅 Morning: {times[0]}\n"
        f"☀️ Afternoon: {times[1]}\n"
        f"🌙 Evening: {times[2]}",
        parse_mode=ParseMode.HTML,
        reply_markup=remove_keyboard()
    )
    
    # Then show profile review
    await show_profile_review(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "notify_custom", Registration.notification_setup)
async def notify_custom(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Start custom notification time setup."""
    current_state = await state.get_state()
    if current_state != Registration.notification_setup:
        await callback.answer("⚠️ This action is no longer available.", show_alert=True)
        return
    
    await disable_old_message_buttons(callback.message)
    
    await callback.message.answer(
        "⏰ <b>Custom Notification Setup</b>\n\n"
        "Please enter <b>3 times</b> for your daily check-ins in HH:MM format.\n"
        "Send them in one message, separated by commas.\n\n"
        "<b>Example:</b> <code>08:00, 14:30, 21:00</code>\n\n"
        "Format: Morning, Afternoon, Evening",
        reply_markup=create_back_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.message(Registration.notification_setup)
async def process_custom_notifications(message: types.Message, state: FSMContext) -> None:
    """Process custom notification times input."""
    if message.text == BTN_BACK:
        await state.set_state(Registration.habit_tracking)
        data = await state.get_data()
        selected = data.get("selected_habits", [])
        return await message.answer(
            PROMPT_HABITS,
            reply_markup=create_habits_keyboard(selected),
            parse_mode=ParseMode.HTML
        )
    
    times_raw = [t.strip() for t in message.text.split(',')]
    
    if len(times_raw) != 3:
        return await message.answer(
            "⚠️ Please enter exactly <b>3 times</b> separated by commas.\n"
            "Example: <code>08:00, 14:30, 21:00</code>",
            parse_mode=ParseMode.HTML
        )
    
    validated_times = []
    for time_str in times_raw:
        validated_time = validate_time(time_str)
        if not validated_time:
            return await message.answer(
                f"⚠️ Invalid time format: <code>{time_str}</code>\n"
                f"Please use HH:MM format (e.g., 08:00)",
                parse_mode=ParseMode.HTML
            )
        validated_times.append(validated_time)
    
    await state.update_data(
        use_default_notifications=False,
        notification_times=validated_times
    )
    
    # Show confirmation
    await message.answer(
        f"✅ <b>Custom times set:</b>\n"
        f"🌅 Morning: {validated_times[0]}\n"
        f"☀️ Afternoon: {validated_times[1]}\n"
        f"🌙 Evening: {validated_times[2]}",
        parse_mode=ParseMode.HTML,
        reply_markup=remove_keyboard()
    )
    
    # Then show profile review
    await show_profile_review(message, state)


# ============================================================================
# PROFILE REVIEW & SAVE
# ============================================================================

async def show_profile_review(message: types.Message, state: FSMContext) -> None:
    """Display profile review for user confirmation."""
    data = await state.get_data()
    
    habits_list = ", ".join(data.get("selected_habits", [])) or "None"
    notification_times = data.get("notification_times", [])
    
    if notification_times and len(notification_times) == 3:
        notif_display = (
            f"🌅 Morning: {notification_times[0]}\n"
            f"☀️ Afternoon: {notification_times[1]}\n"
            f"🌙 Evening: {notification_times[2]}"
        )
    else:
        notif_display = "Not set"
    
    review_text = (
        f"<b>📋 Profile Review:</b>\n\n"
        f"👤 <b>Gender:</b> {escape_html(data['gender'])}, {escape_html(data['age'])} y.o\n"
        f"⚖️ <b>Body:</b> {escape_html(data['height'])}cm, {escape_html(data['weight'])}kg\n"
        f"🏃 <b>Activity:</b> {escape_html(data['activity_level'])}\n"
        f"😴 <b>Schedule:</b> {escape_html(data['bedtime_usual'])} - {escape_html(data['wakeuptime_usual'])}\n"
        f"🛠 <b>Habits:</b> {escape_html(habits_list)}\n"
        f"🌍 <b>Timezone:</b> {escape_html(data['timezone'])}\n\n"
        f"<b>📲 Notifications:</b>\n{escape_html(notif_display)}"
    )
    
    await message.answer(
        review_text,
        reply_markup=create_final_confirm_keyboard(),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "save_profile")
async def save_profile(callback: types.CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Save user profile to database."""
    current_state = await state.get_state()
    if not current_state or not str(current_state).startswith("Registration"):
        await callback.answer("⚠️ Profile already saved or session expired.", show_alert=True)
        return
    
    data = await state.get_data()
    
    profile_data = {
        "telegram_id": callback.from_user.id,
        "first_name": callback.from_user.first_name,
        "gender": data['gender'],
        "age": data['age'],
        "height": data['height'],
        "weight": data['weight'],
        "activity_level": data['activity_level'],
        "bedtime_usual": data['bedtime_usual'],
        "wakeuptime_usual": data['wakeuptime_usual'],
        "timezone": data['timezone'],
        "habits": data.get("selected_habits", []),
        "use_default_notifications": data['use_default_notifications'],
        "notification_times": data['notification_times']
    }
    
    result = await create_profile(profile_data)
    
    if result:
        await disable_old_message_buttons(callback.message)
        
        await schedule_user_notifications(
            bot,
            callback.from_user.id,
            data['notification_times'],
            data['timezone']
        )
        
        notification_times = data['notification_times']
        notif_display = ""
        if notification_times and len(notification_times) >= 3:
            notif_display = (
                f"\n🌅 <b>Morning:</b> {notification_times[0]}"
                f"\n☀️ <b>Afternoon:</b> {notification_times[1]}"
                f"\n🌙 <b>Evening:</b> {notification_times[2]}"
            )
        
        welcome_message = (
            f"✅ <b>Profile created successfully!</b> 🎉\n\n"
            f"<b>Here's how I'll help you:</b>\n\n"
            f"📊 <b>3 Daily Check-ins:</b>\n"
            f"I'll remind you 3 times a day to log how you feel:\n"
            f"{notif_display}\n\n"
            f"❓ <b>Answer Quick Questions:</b>\n"
            f"• <b>Morning:</b> Sleep quality, mood, energy level\n"
            f"• <b>Afternoon:</b> Current mood, energy, stress level\n"
            f"• <b>Evening:</b> Day satisfaction, mood, reflection\n\n"
            f"📈 <b>AI Analysis:</b>\n"
            f"I'll track patterns in your sleep, mood, and habits to give you insights about yourself.\n\n"
            f"🎯 <b>Get Started:</b>\n"
            f"Use /morning /day /evening to start a check-in anytime, or wait for automated reminders.\n\n"
            f"<b>Commands:</b>\n"
            f"• /my_profile — See your profile data\n"
            f"• /weekly_report — View this week's progress\n"
            f"• /edit_profile — Update your information\n"
            f"• /jobs — Check your notification schedule\n"
            f"• /help — Get full command list\n\n"
            f"Ready to track your life? 🚀"
        )
        
        await callback.message.answer(
            welcome_message,
            reply_markup=remove_keyboard(),
            parse_mode=ParseMode.HTML
        )
        logger.info(f"Profile created for user {callback.from_user.id}")
    else:
        await disable_old_message_buttons(callback.message)
        
        await callback.message.answer(
            MSG_DB_ERROR,
            reply_markup=remove_keyboard()
        )
        logger.error(f"Failed to create profile for user {callback.from_user.id}")
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "start_over")
async def start_over(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Restart registration from beginning."""
    await disable_old_message_buttons(callback.message)
    
    await state.clear()
    await state.set_state(Registration.gender)
    await callback.message.answer(
        "🔄 <b>Starting over...</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=remove_keyboard()
    )
    await callback.message.answer(
        PROMPT_GENDER,
        reply_markup=create_gender_keyboard()
    )
    await callback.answer()