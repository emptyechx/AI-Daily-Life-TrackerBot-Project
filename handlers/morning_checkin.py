"""Morning check-in flow handlers."""

import logging
import random
from datetime import date
from typing import Union

from aiogram import Router, F, types
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from handlers.states import MorningCheckin
from keyboards.builders import create_rating_keyboard, create_wakeup_keyboard, create_skip_keyboard, remove_keyboard
from database.daily_entries_db import (
    upsert_entry,
    get_previous_entry,
    should_ask_conditional,
    mark_entry_completed,
    get_entry_by_date_type
)
from database.supabase_db import get_user_profile
from utils.constants import BTN_SKIP, MSG_INVALID_TIME
from utils.validators import validate_text_input, validate_time

router = Router()
logger = logging.getLogger(__name__)

# ============================================================================
# CONDITIONAL QUESTIONS
# ============================================================================

MORNING_QUESTIONS = {
    'sleep_low': [
        "What hindered your sleep: difficulty falling asleep, waking up at night, or just not enough time?",
        "What do you think was the main cause of poor sleep today?",
        "Is it physical fatigue or did your brain just fail to 'switch off'?"
    ],
    'mood_low': [
        "What's affecting your mood: specific plans for today or just your general state?",
        "Is it physical heaviness or a lack of motivation to start the day?"
    ],
    'energy_low': [
        "Is it physical heaviness or a lack of motivation to start the day?",
        "What's draining your energy this morning?"
    ],
    'all_perfect': [
        "Wow! You're at your peak. What helped you wake up in such a perfect state?"
    ]
}


# ============================================================================
# CHECK-IN START
# ============================================================================

@router.message(F.text == "/morning")
async def start_morning_checkin(message: types.Message, state: FSMContext) -> None:
    """Initialize morning check-in flow."""
    user_id = message.from_user.id

    profile = await get_user_profile(user_id)
    if not profile:
        return await message.answer(
            "Please create your profile first with /start",
            reply_markup=remove_keyboard()
        )

    today = date.today()
    existing = await get_entry_by_date_type(user_id, today, 'morning')
    if existing and existing.get('completed_at'):
        return await message.answer(
            "✅ You've already completed your morning check-in today!\n"
            "See you at your day check-in! 😊",
            reply_markup=remove_keyboard()
        )

    await state.set_state(MorningCheckin.sleep_quality)
    await state.update_data(
        entry_date=today.isoformat(),
        user_habits=profile.get('habits', [])
    )

    await message.answer(
        "🌅 <b>Good morning!</b> Let's start your day.\n\n"
        "How was your sleep quality?",
        reply_markup=create_rating_keyboard(),
        parse_mode=ParseMode.HTML
    )


# ============================================================================
# RATING HANDLERS
# ============================================================================

@router.callback_query(MorningCheckin.sleep_quality, F.data.startswith("rate_"))
async def process_sleep_quality(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Process sleep quality rating."""
    try:
        rating = int(callback.data.split("_")[1])
        if not (1 <= rating <= 5):
            await callback.answer("Invalid rating. Please select 1-5.", show_alert=True)
            return
    except (IndexError, ValueError):
        await callback.answer("Invalid data. Please try again.", show_alert=True)
        logger.error(f"Invalid callback data in sleep_quality: {callback.data}")
        return
    
    await state.update_data(sleep_quality=rating)

    user_id = callback.from_user.id
    today = date.today()
    await upsert_entry(user_id, today, 'morning', {'sleep_quality': rating})

    await callback.answer()
    await callback.message.answer(
        "😊 How's your mood this morning?",
        reply_markup=create_rating_keyboard()
    )
    await state.set_state(MorningCheckin.mood)


@router.callback_query(MorningCheckin.mood, F.data.startswith("rate_"))
async def process_mood(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Process mood rating."""
    try:
        rating = int(callback.data.split("_")[1])
        if not (1 <= rating <= 5):
            await callback.answer("Invalid rating. Please select 1-5.", show_alert=True)
            return
    except (IndexError, ValueError):
        await callback.answer("Invalid data. Please try again.", show_alert=True)
        logger.error(f"Invalid callback data in mood: {callback.data}")
        return
    
    await state.update_data(mood=rating)

    user_id = callback.from_user.id
    today = date.today()
    await upsert_entry(user_id, today, 'morning', {'mood': rating})

    await callback.answer()
    await callback.message.answer(
        "⚡ What's your energy level?",
        reply_markup=create_rating_keyboard()
    )
    await state.set_state(MorningCheckin.energy)


@router.callback_query(MorningCheckin.energy, F.data.startswith("rate_"))
async def process_energy(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Process energy level rating."""
    try:
        rating = int(callback.data.split("_")[1])
        if not (1 <= rating <= 5):
            await callback.answer("Invalid rating. Please select 1-5.", show_alert=True)
            return
    except (IndexError, ValueError):
        await callback.answer("Invalid data. Please try again.", show_alert=True)
        logger.error(f"Invalid callback data in energy: {callback.data}")
        return
    
    await state.update_data(energy=rating)

    user_id = callback.from_user.id
    today = date.today()
    await upsert_entry(user_id, today, 'morning', {'energy': rating})

    await callback.answer()
    await callback.message.answer(
        "⏰ Did you wake up on time?",
        reply_markup=create_wakeup_keyboard()
    )
    await state.set_state(MorningCheckin.wakeup_time)


# ============================================================================
# WAKEUP TIME HANDLERS
# ============================================================================

@router.callback_query(MorningCheckin.wakeup_time, F.data == "wakeup_ontime")
async def process_wakeup_ontime(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Handle on-time wakeup."""
    await state.update_data(wakeup_on_time=True)

    user_id = callback.from_user.id
    today = date.today()
    await upsert_entry(user_id, today, 'morning', {'wakeup_on_time': True})

    await callback.answer()
    await check_conditional_question(callback, state)


@router.callback_query(MorningCheckin.wakeup_time, F.data == "wakeup_late")
async def process_wakeup_late(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Handle late wakeup - ask for actual time."""
    await state.update_data(wakeup_on_time=False)

    user_id = callback.from_user.id
    today = date.today()
    await upsert_entry(user_id, today, 'morning', {'wakeup_on_time': False})

    await callback.answer()
    await callback.message.answer(
        "What time did you actually wake up? (HH:MM)",
        reply_markup=create_skip_keyboard()
    )
    await state.set_state(MorningCheckin.actual_wakeup_time)


@router.message(MorningCheckin.actual_wakeup_time)
async def process_actual_wakeup(message: types.Message, state: FSMContext) -> None:
    """
    Process actual wakeup time input.

    """
    if message.text == BTN_SKIP:
        await check_conditional_question(message, state)
        return

    # ⭐ FIX: Use same validation function as registration
    wakeup_time_str = validate_time(message.text.strip())
    
    if not wakeup_time_str:
        # Invalid time format
        await message.answer(
            MSG_INVALID_TIME,
            reply_markup=create_skip_keyboard()
        )
        return
    
    # Valid time - save it
    await state.update_data(actual_wakeup_time=wakeup_time_str)

    user_id = message.from_user.id
    today = date.today()
    await upsert_entry(user_id, today, 'morning', {
        'actual_wakeup_time': wakeup_time_str
    })

    await check_conditional_question(message, state)


# ============================================================================
# CONDITIONAL QUESTION LOGIC
# ============================================================================

async def check_conditional_question(
    event: Union[CallbackQuery, Message],
    state: FSMContext
) -> None:
    """Determine if conditional question should be asked based on ratings."""
    target_message = event.message if isinstance(event, CallbackQuery) else event
    user_id = event.from_user.id
    data = await state.get_data()

    current_ratings = {
        'sleep_quality': data.get('sleep_quality'),
        'mood': data.get('mood'),
        'energy': data.get('energy')
    }

    today = date.today()
    previous = await get_previous_entry(user_id, 'morning', today)

    should_ask, question_type = should_ask_conditional(
        current_ratings,
        previous,
        'morning'
    )

    if should_ask:
        question = random.choice(MORNING_QUESTIONS.get(question_type, []))

        await state.update_data(conditional_question=question)

        await upsert_entry(user_id, today, 'morning', {
            'conditional_question': question
        })

        await target_message.answer(
            f"💭 {question}",
            reply_markup=create_skip_keyboard()
        )
        await state.set_state(MorningCheckin.conditional_answer)
    else:
        await show_habits_reminder(target_message, state)


@router.message(MorningCheckin.conditional_answer)
async def process_conditional_answer(message: types.Message, state: FSMContext) -> None:
    """Process answer to conditional question."""
    if message.text != BTN_SKIP:
        # Validate input length
        is_valid, cleaned = validate_text_input(message.text, max_length=1000)
        
        if not is_valid:
            return await message.answer(
                "⚠️ Response too long. Please keep it under 1000 characters.",
                reply_markup=create_skip_keyboard()
            )
        
        user_id = message.from_user.id
        today = date.today()
        await upsert_entry(user_id, today, 'morning', {
            'conditional_answer': cleaned
        })
        await state.update_data(conditional_answer=cleaned)

    await show_habits_reminder(message, state)


# ============================================================================
# HABITS & NOTES
# ============================================================================

async def show_habits_reminder(message: types.Message, state: FSMContext) -> None:
    """Show user's tracked habits and ask for notes."""
    data = await state.get_data()
    habits = data.get('user_habits', [])

    if habits:
        habits_text = "\n".join([f"• {habit}" for habit in habits])
        await message.answer(
            f"🛠 <b>Don't forget your habits:</b>\n{habits_text}",
            reply_markup=create_skip_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    await message.answer(
        "📝 <b>Any notes for your morning?</b>",
        reply_markup=create_skip_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(MorningCheckin.notes)


@router.message(MorningCheckin.notes)
async def process_notes(message: types.Message, state: FSMContext) -> None:
    """Process final notes and complete check-in."""
    user_id = message.from_user.id
    today = date.today()

    if message.text != BTN_SKIP:
        # Validate input length
        is_valid, cleaned = validate_text_input(message.text, max_length=1000)
        
        if not is_valid:
            return await message.answer(
                "⚠️ Notes too long. Please keep it under 1000 characters.",
                reply_markup=create_skip_keyboard()
            )
        
        await upsert_entry(user_id, today, 'morning', {
            'user_notes': cleaned
        })

    # Get entry and mark as completed
    entry = await get_entry_by_date_type(user_id, today, 'morning')
    if entry:
        await mark_entry_completed(entry['id'])
    else:
        logger.error(f"No entry found to mark complete for user {user_id} on {today}")

    profile = await get_user_profile(user_id)
    if profile and profile.get('use_default_notifications'):
        times = profile.get('notification_times', [])
        next_time = times[1] if len(times) > 1 else "afternoon"
    else:
        next_time = "afternoon"

    await message.answer(
        "✅ <b>Morning check-in complete!</b>\n\n"
        f"Great start! I'll check in with you again around {next_time}. "
        "Have a productive day! 💪",
        reply_markup=remove_keyboard(),
        parse_mode=ParseMode.HTML
    )

    await state.clear()
    logger.info(f"Morning check-in completed for user {user_id}")