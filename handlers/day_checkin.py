import random
from datetime import date
import logging
from aiogram import Router, F, types
from aiogram.types import CallbackQuery, Message
from aiogram.enums import ParseMode
from typing import Union
from aiogram.fsm.context import FSMContext
from handlers.states import DayCheckin
from keyboards.builders import create_rating_keyboard, create_skip_keyboard, remove_keyboard
from database.daily_entries_db import (
    upsert_entry, get_previous_entry, should_ask_conditional,
    mark_entry_completed, get_entry_by_date_type
)
from database.supabase_db import get_user_profile
from utils.constants import BTN_SKIP
from utils.validators import validate_text_input

router = Router()
logger = logging.getLogger(__name__)

DAY_QUESTIONS = {
    'mood_low': [
        "If you could pause the day right now, what would you change first?",
        "What's weighing on your mind right now?"
    ],
    'energy_low': [
        "Energy dropped sharply. Is it exhaustion or just a mid-day slump?",
        "What's draining your energy most right now?"
    ],
    'mood_drop': [
        "Your mood shifted. What happened between this morning and now?",
        "If you could pause the day right now, what would you change first?"
    ],
    'energy_drop': [
        "Energy dropped sharply. Is it exhaustion or just a mid-day slump?",
        "What changed since this morning that's affecting your energy?"
    ],
    'stress_high': [
        "Is this work pressure, a conflict, or internal anxiety?",
        "How is this stress manifesting in your body (tension, headache)?"
    ],
    'stress_spike': [
        "Stress spiked. What was the trigger?",
        "Is this work pressure, a conflict, or internal anxiety?"
    ],
    'all_perfect': [
        "You're crushing it today! What's your secret? 🌟"
    ]
}

@router.message(F.text == "/day")
async def start_day_checkin(message: types.Message, state: FSMContext) -> None:
    user_id = message.from_user.id

    profile = await get_user_profile(user_id)
    if not profile:
        return await message.answer(
            "Please create your profile first with /start",
            reply_markup=remove_keyboard()
        )

    today = date.today()
    existing = await get_entry_by_date_type(user_id, today, 'day')
    if existing and existing.get('completed_at'):
        return await message.answer(
            "✅ You've already completed your day check-in today!\n"
            "See you at your evening check-in! 🙂",
            reply_markup=remove_keyboard()
        )

    await state.set_state(DayCheckin.mood)
    await state.update_data(entry_date=today.isoformat())

    await message.answer(
        "☀️ <b>Mid-day check-in!</b>\n\n"
        "How's your mood right now?",
        reply_markup=create_rating_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.callback_query(DayCheckin.mood, F.data.startswith("rate_"))
async def process_mood(callback: types.CallbackQuery, state: FSMContext) -> None:
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
    await upsert_entry(user_id, today, 'day', {'mood': rating})

    await callback.answer()
    await callback.message.answer(
        "🔋 How's your energy level?",
        reply_markup=create_rating_keyboard()
    )
    await state.set_state(DayCheckin.energy)

@router.callback_query(DayCheckin.energy, F.data.startswith("rate_"))
async def process_energy(callback: types.CallbackQuery, state: FSMContext) -> None:
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
    await upsert_entry(user_id, today, 'day', {'energy': rating})

    await callback.answer()
    await callback.message.answer(
        "😵 What's your stress level?",
        reply_markup=create_rating_keyboard()
    )
    await state.set_state(DayCheckin.stress)

@router.callback_query(DayCheckin.stress, F.data.startswith("rate_"))
async def process_stress(callback: types.CallbackQuery, state: FSMContext) -> None:
    try:
        rating = int(callback.data.split("_")[1])
        if not (1 <= rating <= 5):
            await callback.answer("Invalid rating. Please select 1-5.", show_alert=True)
            return
    except (IndexError, ValueError):
        await callback.answer("Invalid data. Please try again.", show_alert=True)
        logger.error(f"Invalid callback data in stress: {callback.data}")
        return
    
    await state.update_data(stress=rating)

    user_id = callback.from_user.id
    today = date.today()
    await upsert_entry(user_id, today, 'day', {'stress': rating})

    await callback.answer()
    await check_conditional_question(callback, state)

async def check_conditional_question(event: Union[CallbackQuery, Message], state: FSMContext) -> None:
    target_message = event.message if isinstance(event, CallbackQuery) else event
    user_id = event.from_user.id

    data = await state.get_data()

    current_ratings = {
        'mood': data.get('mood'),
        'energy': data.get('energy'),
        'stress': data.get('stress')
    }

    today = date.today()
    previous = await get_previous_entry(user_id, 'day', today)

    should_ask, question_type = should_ask_conditional(current_ratings, previous, 'day')

    if should_ask:
        question = random.choice(DAY_QUESTIONS.get(question_type, []))

        await state.update_data(conditional_question=question)

        await upsert_entry(user_id, today, 'day', {
            'conditional_question': question
        })

        await target_message.answer(
            f"💡 {question}",
            reply_markup=create_skip_keyboard()
        )
        await state.set_state(DayCheckin.conditional_answer)
    else:
        await show_focus_reminder(target_message, state)

@router.message(DayCheckin.conditional_answer)
async def process_conditional_answer(message: types.Message, state: FSMContext) -> None:
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
        await upsert_entry(user_id, today, 'day', {
            'conditional_answer': cleaned
        })
        await state.update_data(conditional_answer=cleaned)

    await show_focus_reminder(message, state)

async def show_focus_reminder(message: types.Message, state: FSMContext) -> None:
    await message.answer(
        "💪 <b>You're halfway through the day!</b>\n\n"
        "Keep up the momentum! 🚀\n\n"
        "📝 <b>Any quick notes about your day so far?</b>\n"
        "(e.g., what went well, what's challenging, or anything on your mind)",
        reply_markup=create_skip_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(DayCheckin.notes)

@router.message(DayCheckin.notes)
async def process_notes(message: types.Message, state: FSMContext) -> None:
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
        
        await upsert_entry(user_id, today, 'day', {
            'user_notes': cleaned
        })

    # Get entry and mark as completed
    entry = await get_entry_by_date_type(user_id, today, 'day')
    if entry:
        await mark_entry_completed(entry['id'])
    else:
        logger.error(f"No entry found to mark complete for user {user_id} on {today}")

    profile = await get_user_profile(user_id)
    if profile and profile.get('use_default_notifications'):
        times = profile.get('notification_times', [])
        next_time = times[2] if len(times) > 2 else "evening"
    else:
        next_time = "evening"

    await message.answer(
        "✅ <b>Day check-in complete!</b>\n\n"
        f"Great job! I'll see you this {next_time} for your final check-in. Keep it up! 💪",
        reply_markup=remove_keyboard(),
        parse_mode=ParseMode.HTML
    )

    await state.clear()
    logger.info(f"Day check-in completed for user {user_id}")
