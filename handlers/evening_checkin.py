import random
from datetime import date
import logging
from aiogram import Router, F, types
from aiogram.types import CallbackQuery, Message
from typing import Union
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from handlers.states import EveningCheckin
from keyboards.builders import (
    create_rating_keyboard, 
    create_satisfaction_keyboard, 
    create_skip_keyboard, 
    remove_keyboard
)
from database.daily_entries_db import (
    upsert_entry, get_previous_entry, should_ask_conditional,
    mark_entry_completed, get_entry_by_date_type
)
from database.supabase_db import get_user_profile
from utils.constants import BTN_SKIP
from utils.validators import validate_text_input

router = Router()
logger = logging.getLogger(__name__)

EVENING_QUESTIONS = {
    'mood_low': [
        "If you could rewind the day, what would you change first?",
        "What exactly was missing today for you to feel satisfied?"
    ],
    'stress_high': [
        "Stress spiked this evening. What was the 'last straw' today?",
        "What thought is currently preventing you from relaxing?"
    ],
    'stress_spike': [
        "Stress rose sharply. What happened this evening?",
        "What thought is currently preventing you from relaxing?"
    ],
    'satisfaction_low': [
        "If you could rewind the day, what would you change first?",
        "What exactly was missing today for you to feel satisfied?"
    ],
    'all_perfect': [
        "Perfect day! What made today so special? 🌟"
    ]
}

@router.message(F.text == "/evening")
async def start_evening_checkin(message: types.Message, state: FSMContext) -> None:
    user_id = message.from_user.id

    profile = await get_user_profile(user_id)
    if not profile:
        return await message.answer(
            "Please create your profile first with /start",
            reply_markup=remove_keyboard()
        )

    today = date.today()
    existing = await get_entry_by_date_type(user_id, today, 'evening')
    if existing and existing.get('completed_at'):
        return await message.answer(
            "✅ You've already completed your evening check-in today!\n"
            "Great work today! See you tomorrow morning! 🌙",
            reply_markup=remove_keyboard()
        )

    await state.set_state(EveningCheckin.satisfaction)
    await state.update_data(entry_date=today.isoformat())

    await message.answer(
        "🌙 <b>Evening reflection time!</b>\n\n"
        "How satisfied are you with your day?",
        reply_markup=create_satisfaction_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.callback_query(EveningCheckin.satisfaction, F.data.startswith("satisfaction_"))
async def process_satisfaction(callback: types.CallbackQuery, state: FSMContext) -> None:
    satisfaction = callback.data == "satisfaction_good"
    await state.update_data(daily_satisfaction=satisfaction)

    user_id = callback.from_user.id
    today = date.today()
    await upsert_entry(user_id, today, 'evening', {'daily_satisfaction': satisfaction})

    await callback.answer()
    await callback.message.answer(
        "😊 How's your mood this evening?",
        reply_markup=create_rating_keyboard()
    )
    await state.set_state(EveningCheckin.mood)

@router.callback_query(EveningCheckin.mood, F.data.startswith("rate_"))
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
    await upsert_entry(user_id, today, 'evening', {'mood': rating})

    await callback.answer()
    await callback.message.answer(
        "😰 What's your stress level now?",
        reply_markup=create_rating_keyboard()
    )
    await state.set_state(EveningCheckin.stress)

@router.callback_query(EveningCheckin.stress, F.data.startswith("rate_"))
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
    await upsert_entry(user_id, today, 'evening', {'stress': rating})

    await callback.answer()
    await check_conditional_question(callback, state)

async def check_conditional_question(event: Union[CallbackQuery, Message], state: FSMContext) -> None:
    target_message = event.message if isinstance(event, CallbackQuery) else event
    user_id = event.from_user.id
    data = await state.get_data()

    current_ratings = {
        'mood': data.get('mood'),
        'stress': data.get('stress'),
        'satisfaction': data.get('daily_satisfaction')
    }

    today = date.today()
    previous = await get_previous_entry(user_id, 'evening', today)

    should_ask = False
    question_type = ''

    if not current_ratings.get('satisfaction'):
        should_ask = True
        question_type = 'satisfaction_low'
    elif current_ratings.get('mood', 0) <= 2:
        should_ask = True
        question_type = 'mood_low'
    elif current_ratings.get('stress', 0) >= 4:
        should_ask = True
        question_type = 'stress_high'
    elif previous and current_ratings.get('stress', 0) - previous.get('stress', 3) >= 2:
        should_ask = True
        question_type = 'stress_spike'
    elif current_ratings.get('satisfaction') and current_ratings.get('mood', 0) == 5 and current_ratings.get('stress', 0) == 1:
        should_ask = True
        question_type = 'all_perfect'

    if should_ask:
        question = random.choice(EVENING_QUESTIONS.get(question_type, []))

        await state.update_data(conditional_question=question)

        await upsert_entry(user_id, today, 'evening', {
            'conditional_question': question
        })

        await target_message.answer(
            f"💭 {question}",
            reply_markup=create_skip_keyboard()
        )
        await state.set_state(EveningCheckin.conditional_answer)
    else:
        await ask_for_reflection(target_message, state)

@router.message(EveningCheckin.conditional_answer)
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
        await upsert_entry(user_id, today, 'evening', {
            'conditional_answer': cleaned
        })
        await state.update_data(conditional_answer=cleaned)

    await ask_for_reflection(message, state)


async def ask_for_reflection(message: types.Message, state: FSMContext) -> None:
    await message.answer(
        "📝 <b>Final reflection:</b> Any thoughts on your day?",
        reply_markup=create_skip_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(EveningCheckin.reflection)


@router.message(EveningCheckin.reflection)
async def process_reflection(message: types.Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    today = date.today()

    if message.text != BTN_SKIP:
        # Validate input length
        is_valid, cleaned = validate_text_input(message.text, max_length=1000)
        
        if not is_valid:
            return await message.answer(
                "⚠️ Reflection too long. Please keep it under 1000 characters.",
                reply_markup=create_skip_keyboard()
            )
        
        await upsert_entry(user_id, today, 'evening', {
            'day_reflection': cleaned
        })

    # Get entry and mark as completed
    entry = await get_entry_by_date_type(user_id, today, 'evening')
    if entry:
        await mark_entry_completed(entry['id'])
    else:
        logger.error(f"No entry found to mark complete for user {user_id} on {today}")

    await message.answer(
        "✅ <b>Evening check-in complete!</b>\n\n"
        "Great work today! Rest well and see you tomorrow morning! 🌙",
        reply_markup=remove_keyboard(),
        parse_mode=ParseMode.HTML
    )

    await state.clear()
    logger.info(f"Evening check-in completed for user {user_id}")
