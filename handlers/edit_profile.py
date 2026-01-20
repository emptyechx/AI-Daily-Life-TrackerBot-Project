import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode

from database.supabase_db import get_user_profile, update_user_profile
from scheduler import reschedule_user_notifications
from utils.validators import (
    escape_html,
    validate_integer,
    validate_float,
    validate_time,
    calculate_notification_defaults,
    validate_timezone,
    format_timezone_suggestions,
)
from keyboards.builders import (
    create_edit_profile_keyboard,
    create_gender_keyboard,
    create_activity_keyboard,
    create_edit_habits_keyboard,
    remove_keyboard,
)
from utils.navigation import validate_button_choice
from utils.constants import (
    GENDERS,
    ACTIVITY_LEVELS,
    AGE_MIN,
    AGE_MAX,
    HEIGHT_MIN,
    HEIGHT_MAX,
    WEIGHT_MIN,
    WEIGHT_MAX,
)

router = Router()
logger = logging.getLogger(__name__)


class EditProfileStates(StatesGroup):
    """States for profile editing flow."""
    waiting_for_input = State()
    editing_habits = State()
    editing_notifications = State()


def _format_profile(profile: dict) -> str:
    """
    Format profile data into readable text.
    
    Args:
        profile: User profile dictionary
    
    Returns:
        Formatted HTML string
    """
    name = profile.get("first_name", "N/A")
    gender = profile.get("gender", "N/A")
    age = profile.get("age", "N/A")
    height = profile.get("height", "N/A")
    weight = profile.get("weight", "N/A")
    activity = profile.get("activity_level", "N/A")
    bedtime = profile.get("bedtime_usual", "N/A")
    wakeup = profile.get("wakeuptime_usual", "N/A")
    timezone = profile.get("timezone", "UTC")
    habits = ", ".join(profile.get("habits", [])) or "None"
    notification_times = ", ".join(profile.get("notification_times", [])) or "Not set"

    return (
        f"👤 <b>Profile:</b> {escape_html(name)}\n\n"
        f"📊 <b>Stats:</b> {escape_html(gender)}, {escape_html(age)} y.o, {escape_html(height)}cm, {escape_html(weight)}kg\n"
        f"🏃 <b>Activity:</b> {escape_html(activity)}\n"
        f"😴 <b>Sleep:</b> {escape_html(bedtime)} - {escape_html(wakeup)}\n"
        f"🛠 <b>Trackers:</b> {escape_html(habits)}\n"
        f"📲 <b>Notifications:</b> {escape_html(notification_times)}\n"
        f"🌍 <b>Timezone:</b> {escape_html(timezone)}\n\n"
        f"Select a field to edit:"
    )


async def update_user_schedule(message: types.Message, user_id: int) -> None:
    """
    Update user's notification schedule after profile changes.
    Called when sleep times or timezone changes.
    
    Args:
        message: Message object to send updates
        user_id: User's Telegram ID
    """
    try:
        # Get updated profile
        profile = await get_user_profile(user_id)
        
        if not profile:
            logger.error(f"Cannot update schedule: profile not found for user {user_id}")
            return
        
        # Check if using default notifications
        use_default = profile.get('use_default_notifications', True)
        
        if use_default:
            # Recalculate times based on new sleep schedule
            bedtime = profile.get('bedtime_usual')
            wakeup = profile.get('wakeuptime_usual')
            
            if bedtime and wakeup:
                new_times = calculate_notification_defaults(wakeup, bedtime)
                
                # Update in database
                await update_user_profile(user_id, {
                    'notification_times': new_times
                })
                
                notification_times = new_times
            else:
                logger.error(f"Missing sleep times for user {user_id}")
                return
        else:
            # Use existing custom times
            notification_times = profile.get('notification_times', [])
        
        # Get timezone
        timezone = profile.get('timezone', 'UTC')
        
        # Reschedule notifications
        bot = message.bot
        success = await reschedule_user_notifications(
            bot,
            user_id,
            notification_times,
            timezone
        )
        
        if success:
            times_display = (
                f"🌅 Morning: {notification_times[0]}\n"
                f"☀️ Day: {notification_times[1]}\n"
                f"🌙 Evening: {notification_times[2]}"
            )
            
            await message.answer(
                f"✅ <b>Notification schedule updated!</b>\n\n"
                f"{times_display}\n\n"
                f"<i>Your reminders have been rescheduled.</i>",
                parse_mode=ParseMode.HTML
            )
            
            logger.info(f"✅ Schedule updated for user {user_id}")
        else:
            await message.answer(
                "⚠️ Schedule partially updated. Use /reload_schedule if needed.",
                parse_mode=ParseMode.HTML
            )
            logger.warning(f"⚠️ Partial schedule update for user {user_id}")
            
    except Exception as e:
        logger.error(f"❌ Error updating schedule for user {user_id}: {e}", exc_info=True)
        await message.answer(
            "⚠️ Could not update notification schedule. Use /reload_schedule to fix.",
            parse_mode=ParseMode.HTML
        )


# ============================================================================
# MAIN EDIT PROFILE COMMAND
# ============================================================================

@router.message(F.text == "/edit_profile")
async def cmd_edit_profile(message: types.Message, state: FSMContext) -> None:
    """Start profile editing - show current profile with edit menu."""
    user_id = message.from_user.id
    profile = await get_user_profile(user_id)
    
    if not profile:
        return await message.answer(
            "❌ No profile found! Use /start to create one.",
            reply_markup=remove_keyboard()
        )

    text = _format_profile(profile)
    await message.answer(
        text,
        reply_markup=create_edit_profile_keyboard(),
        parse_mode=ParseMode.HTML
    )
    logger.info(f"Edit profile menu shown to user {user_id}")


@router.callback_query(F.data.startswith("edit_"))
async def callback_edit_field(callback: types.CallbackQuery, state: FSMContext) -> None:
    """
    Handle field edit selection.

    """
    # State validation: prevent old button clicks
    current_state = await state.get_state()
    if current_state and current_state in [EditProfileStates.editing_habits, EditProfileStates.editing_notifications]:
        # User is in a different edit flow, ignore this callback
        await callback.answer("⚠️ Please finish your current edit first.", show_alert=True)
        return
    
    field = callback.data.split("edit_")[1]
    user_id = callback.from_user.id
    profile = await get_user_profile(user_id) or {}

    await callback.answer()

    if field == "first_name":
        await state.update_data(edit_field="first_name")
        await state.set_state(EditProfileStates.waiting_for_input)
        await callback.message.answer(
            "Enter new first name:",
            reply_markup=remove_keyboard()
        )
        return

    if field == "gender":
        await state.update_data(edit_field="gender")
        await state.set_state(EditProfileStates.waiting_for_input)
        await callback.message.answer(
            "Select gender:",
            reply_markup=create_gender_keyboard()
        )
        return

    if field == "age":
        await state.update_data(edit_field="age")
        await state.set_state(EditProfileStates.waiting_for_input)
        await callback.message.answer(
            f"Enter new age (number between {AGE_MIN} and {AGE_MAX}):",
            reply_markup=remove_keyboard()
        )
        return

    if field == "height":
        await state.update_data(edit_field="height")
        await state.set_state(EditProfileStates.waiting_for_input)
        await callback.message.answer(
            f"Enter new height in cm (e.g., 175):",
            reply_markup=remove_keyboard()
        )
        return

    if field == "weight":
        await state.update_data(edit_field="weight")
        await state.set_state(EditProfileStates.waiting_for_input)
        await callback.message.answer(
            f"Enter new weight in kg (e.g., 70):",
            reply_markup=remove_keyboard()
        )
        return

    if field == "activity_level":
        await state.update_data(edit_field="activity_level")
        await state.set_state(EditProfileStates.waiting_for_input)
        await callback.message.answer(
            "Select activity level:",
            reply_markup=create_activity_keyboard()
        )
        return

    if field in ("bedtime_usual", "wakeuptime_usual"):
        await state.update_data(edit_field=field)
        await state.set_state(EditProfileStates.waiting_for_input)
        await callback.message.answer(
            "Enter time in HH:MM format (e.g., 23:30):",
            reply_markup=remove_keyboard()
        )
        return

    if field == "habits":
        selected = profile.get("habits", [])
        await state.update_data(selected_habits=selected)
        await state.set_state(EditProfileStates.editing_habits)
        await callback.message.answer(
            "🛠 <b>Edit Habits</b>\n\nToggle habits and press Save:",
            reply_markup=create_edit_habits_keyboard(selected),
            parse_mode=ParseMode.HTML
        )
        return

    if field == "notification_times":
        current_times = profile.get("notification_times", [])
        times_display = ", ".join(current_times) if current_times else "Not set"
        
        await state.update_data(edit_field="notification_times")
        await state.set_state(EditProfileStates.editing_notifications)
        await callback.message.answer(
            f"📲 <b>Edit Notification Times</b>\n\n"
            f"Current times: <code>{times_display}</code>\n\n"
            f"Enter 3 times in HH:MM format, separated by commas.\n"
            f"Example: <code>08:00, 14:30, 21:00</code>",
            reply_markup=remove_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return

    if field == "timezone":
        current_tz = profile.get("timezone", "UTC")
        await state.update_data(edit_field="timezone")
        await state.set_state(EditProfileStates.waiting_for_input)
        await callback.message.answer(
            f"🌍 <b>Edit Timezone</b>\n\n"
            f"Current: <code>{current_tz}</code>\n\n"
            f"Enter your timezone string (e.g., <code>Europe/Kyiv</code>):",
            reply_markup=remove_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return

    if field == "finish_editing":
        await state.clear()
        await callback.message.answer(
            "✅ Editing finished!",
            reply_markup=remove_keyboard()
        )
        logger.info(f"User {user_id} finished editing profile")
        return


# ============================================================================
# HABIT EDITING
# ============================================================================

@router.callback_query(
    F.data.startswith("toggle_habit_"),
    EditProfileStates.editing_habits
)
async def callback_toggle_habit(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Toggle habit selection during editing."""
    # State validation
    current_state = await state.get_state()
    if current_state != EditProfileStates.editing_habits:
        await callback.answer("⚠️ This action is no longer available.", show_alert=True)
        return
    
    habit = callback.data.split("toggle_habit_", 1)[1]
    data = await state.get_data()
    selected = data.get("selected_habits", [])

    if habit in selected:
        selected.remove(habit)
    else:
        selected.append(habit)

    await state.update_data(selected_habits=selected)
    
    try:
        await callback.message.edit_reply_markup(
            reply_markup=create_edit_habits_keyboard(selected)
        )
    except Exception:
        pass
    
    await callback.answer()


@router.callback_query(F.data == "save_habits_edit", EditProfileStates.editing_habits)
async def callback_save_edit_habits(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Save edited habits and return to edit menu."""
    # State validation
    current_state = await state.get_state()
    if current_state != EditProfileStates.editing_habits:
        await callback.answer("⚠️ This action is no longer available.", show_alert=True)
        return
    
    data = await state.get_data()
    selected = data.get("selected_habits", [])
    user_id = callback.from_user.id

    success = await update_user_profile(user_id, {"habits": selected})
    
    if success is None:
        await callback.message.answer("❌ Error saving habits. Please try again.")
        await callback.answer()
        return
    
    await state.clear()
    
    user_profile = await get_user_profile(user_id)
    if user_profile:
        text = _format_profile(user_profile)
        await callback.message.answer(
            "✅ Habits updated!\n\n" + text,
            reply_markup=create_edit_profile_keyboard(),
            parse_mode=ParseMode.HTML
        )
        logger.info(f"Habits updated for user {user_id}: {selected}")
    
    await callback.answer()


@router.callback_query(F.data == "cancel_habits_edit", EditProfileStates.editing_habits)
async def callback_cancel_edit_habits(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Cancel habit editing and return to edit menu."""
    user_id = callback.from_user.id
    
    await state.clear()
    
    user_profile = await get_user_profile(user_id)
    if user_profile:
        text = _format_profile(user_profile)
        await callback.message.answer(
            text,
            reply_markup=create_edit_profile_keyboard(),
            parse_mode=ParseMode.HTML
        )
        logger.info(f"Habit editing cancelled by user {user_id}")
    
    await callback.answer()


# ============================================================================
# TEXT INPUT EDITING
# ============================================================================

@router.message(EditProfileStates.waiting_for_input)
async def process_edit_input(message: types.Message, state: FSMContext) -> None:
    """Process text input for field editing."""
    data = await state.get_data()
    field = data.get("edit_field")
    user_id = message.from_user.id
    text = message.text.strip()

    if not field:
        await message.answer(
            "❌ No field selected. Use /edit_profile to start.",
            reply_markup=remove_keyboard()
        )
        await state.clear()
        return

    # Track if we need to update notification schedule
    needs_job_update = False
    
    # Validate and convert input based on field type
    value = None
    
    if field == "first_name":
        value = text
        
    elif field == "gender":
        valid = await validate_button_choice(message, GENDERS)
        if not valid:
            return
        value = valid
        await message.answer(f"✅ {valid}", reply_markup=remove_keyboard())
        
    elif field == "age":
        is_valid, num = validate_integer(text, AGE_MIN, AGE_MAX)
        if not is_valid:
            await message.answer(f"⚠️ Invalid age. Please enter a number between {AGE_MIN} and {AGE_MAX}:")
            return
        value = num
        
    elif field == "height":
        is_valid, num = validate_float(text, HEIGHT_MIN, HEIGHT_MAX)
        if not is_valid:
            await message.answer(f"⚠️ Invalid height. Please enter a number between {HEIGHT_MIN} and {HEIGHT_MAX} cm:")
            return
        value = num
        
    elif field == "weight":
        is_valid, num = validate_float(text, WEIGHT_MIN, WEIGHT_MAX)
        if not is_valid:
            await message.answer(f"⚠️ Invalid weight. Please enter a number between {WEIGHT_MIN} and {WEIGHT_MAX} kg:")
            return
        value = num
        
    elif field == "activity_level":
        valid = await validate_button_choice(message, ACTIVITY_LEVELS)
        if not valid:
            return
        value = valid
        await message.answer(f"✅ {valid}", reply_markup=remove_keyboard())
        
    elif field in ("bedtime_usual", "wakeuptime_usual"):
        valid_time = validate_time(text)
        if not valid_time:
            await message.answer("⚠️ Invalid time format. Use HH:MM (e.g., 23:30):")
            return
        value = valid_time
        needs_job_update = True  # Sleep times changed
        
    elif field == "timezone":
        validated_tz = validate_timezone(text)
        
        if not validated_tz:
            suggestions = format_timezone_suggestions()
            return await message.answer(
                f"⚠️ Invalid timezone: <code>{text}</code>\n\n{suggestions}",
                parse_mode=ParseMode.HTML
            )
        
        value = validated_tz
        needs_job_update = True  # Timezone changed
        
    else:
        await message.answer(
            "❌ Unsupported field.",
            reply_markup=remove_keyboard()
        )
        await state.clear()
        return

    # Update database
    success = await update_user_profile(user_id, {field: value})
    
    if success is None:
        await message.answer("❌ Error saving profile. Please try again.")
    else:
        # Update jobs if needed
        if needs_job_update:
            await update_user_schedule(message, user_id)
        
        # Fetch updated profile and show edit menu
        user_profile = await get_user_profile(user_id)
        if user_profile:
            text = _format_profile(user_profile)
            await message.answer(
                f"✅ {field.replace('_', ' ').title()} updated!\n\n" + text,
                reply_markup=create_edit_profile_keyboard(),
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Field '{field}' updated for user {user_id}")

    await state.clear()


# ============================================================================
# NOTIFICATION TIMES EDITING
# ============================================================================

@router.message(EditProfileStates.editing_notifications)
async def process_edit_notifications(message: types.Message, state: FSMContext) -> None:
    """Process notification times editing."""
    text = message.text.strip()
    parts = [p.strip() for p in text.split(",")]
    
    if len(parts) != 3:
        return await message.answer(
            "⚠️ Please enter exactly 3 times separated by commas.\n"
            "Example: <code>08:00, 14:30, 21:00</code>",
            parse_mode=ParseMode.HTML
        )
    
    validated = []
    for t in parts:
        vt = validate_time(t)
        if not vt:
            return await message.answer(
                f"⚠️ Invalid time format: <code>{t}</code>\n"
                f"Please use HH:MM format.",
                parse_mode=ParseMode.HTML
            )
        validated.append(vt)

    user_id = message.from_user.id
    success = await update_user_profile(user_id, {"notification_times": validated})
    
    if success is None:
        await message.answer("❌ Error saving notification times.")
    else:
        # Update jobs after notification times change
        await update_user_schedule(message, user_id)
        
        # Fetch updated profile and show edit menu
        user_profile = await get_user_profile(user_id)
        if user_profile:
            text = _format_profile(user_profile)
            await message.answer(
                f"✅ Notification times updated!\n\n" + text,
                reply_markup=create_edit_profile_keyboard(),
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Notification times updated for user {user_id}: {validated}")
    
    await state.clear()