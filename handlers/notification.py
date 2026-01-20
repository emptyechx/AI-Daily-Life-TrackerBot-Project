import logging
from datetime import date

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from handlers.states import MorningCheckin, DayCheckin, EveningCheckin
from keyboards.builders import create_rating_keyboard, create_satisfaction_keyboard, remove_keyboard
from database.daily_entries_db import (
    upsert_entry,
    get_entry_by_date_type,
    increment_remind_later_count
)
from scheduler import schedule_onetime_reminder
from utils.constants import REMIND_LATER_MAX_COUNT

router = Router()
logger = logging.getLogger(__name__)


# ============================================================================
# START CHECK-IN HANDLERS
# ============================================================================

@router.callback_query(F.data == "start_morning")
async def callback_start_morning(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Start morning check-in flow."""
    try:
        await callback.answer()

        user_id = callback.from_user.id
        today = date.today()

        entry = await get_entry_by_date_type(user_id, today, 'morning')
        if entry and entry.get('completed_at'):
            return await callback.message.answer(
                "✅ You've already completed your morning check-in today!",
                reply_markup=remove_keyboard(),
                parse_mode="HTML"
            )

        await state.set_state(MorningCheckin.sleep_quality)
        await state.update_data(entry_date=today.isoformat())

        await callback.message.answer(
            "🌅 <b>Good morning!</b> Let's start your day.\n\n"
            "How was your sleep quality?",
            reply_markup=create_rating_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error starting morning check-in for user {callback.from_user.id}: {e}")
        await callback.answer("Error starting check-in. Please try again.", show_alert=True)


@router.callback_query(F.data == "start_day")
async def callback_start_day(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Start day check-in flow."""
    try:
        await callback.answer()

        user_id = callback.from_user.id
        today = date.today()

        entry = await get_entry_by_date_type(user_id, today, 'day')
        if entry and entry.get('completed_at'):
            return await callback.message.answer(
                "✅ You've already completed your day check-in today!",
                reply_markup=remove_keyboard(),
                parse_mode="HTML"
            )

        await state.set_state(DayCheckin.mood)
        await state.update_data(entry_date=today.isoformat())

        await callback.message.answer(
            "☀️ <b>Mid-day check-in!</b>\n\n"
            "How's your mood right now?",
            reply_markup=create_rating_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error starting day check-in for user {callback.from_user.id}: {e}")
        await callback.answer("Error starting check-in. Please try again.", show_alert=True)


@router.callback_query(F.data == "start_evening")
async def callback_start_evening(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Start evening check-in flow."""
    try:
        await callback.answer()

        user_id = callback.from_user.id
        today = date.today()

        entry = await get_entry_by_date_type(user_id, today, 'evening')
        if entry and entry.get('completed_at'):
            return await callback.message.answer(
                "✅ You've already completed your evening check-in today!",
                reply_markup=remove_keyboard(),
                parse_mode="HTML"
            )

        await state.set_state(EveningCheckin.satisfaction)
        await state.update_data(entry_date=today.isoformat())

        await callback.message.answer(
            "🌙 <b>Evening reflection time!</b>\n\n"
            "How satisfied are you with your day?",
            reply_markup=create_satisfaction_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error starting evening check-in for user {callback.from_user.id}: {e}")
        await callback.answer("Error starting check-in. Please try again.", show_alert=True)


# ============================================================================
# REMIND LATER HANDLERS
# ============================================================================

@router.callback_query(F.data.startswith("remind_later_"))
async def callback_remind_later(callback: types.CallbackQuery) -> None:
    """
    Handle 'Remind me later' button press.
    """
    try:
        # Extract entry type from callback data
        entry_type = callback.data.rsplit("_", 1)[1]

        user_id = callback.from_user.id
        today = date.today()

        # Get or create entry
        entry = await get_entry_by_date_type(user_id, today, entry_type)
        if not entry:
            entry = await upsert_entry(user_id, today, entry_type, {})

        if not entry:
            await callback.answer(
                "❌ Error creating entry. Please try again.",
                show_alert=True
            )
            return

        # Get current remind count
        remind_count = entry.get('remind_later_count', 0)

        # Check if already reminded max times
        if remind_count >= REMIND_LATER_MAX_COUNT:
            await callback.answer(
                "⏰ This was your last reminder! Please complete your check-in now or skip it.",
                show_alert=True
            )
            return

        # Increment remind count in database
        await increment_remind_later_count(entry['id'])
        new_count = remind_count + 1

        try:
            job_id = await schedule_onetime_reminder(
                callback.bot,
                user_id,
                entry_type,
                new_count
            )

            if job_id:
                logger.info(
                    f"✅ One-time reminder scheduled | user={user_id} | "
                    f"type={entry_type} | count={new_count}"
                )

                await callback.answer("⏰ I'll remind you in 15 minutes.")
                await callback.message.answer(
                    "✅ Okay! I'll check back with you in 15 minutes. ⏰",
                    reply_markup=remove_keyboard(),
                    parse_mode="HTML"
                )
            else:
                # If scheduling failed
                await callback.answer(
                    "⚠️ Could not schedule reminder. Please try again.",
                    show_alert=True
                )

        except Exception as sched_error:
            logger.error(f"❌ Scheduler error: {sched_error}", exc_info=True)
            await callback.answer(
                "⚠️ Could not schedule reminder.",
                show_alert=False
            )

    except Exception as e:
        logger.error(f"❌ Error in remind_later for user {callback.from_user.id}: {e}")
        await callback.answer("Error. Please try again.", show_alert=True)


# ============================================================================
# SKIP CHECK-IN HANDLERS
# ============================================================================

@router.callback_query(F.data.startswith("skip_checkin_"))
async def callback_skip_checkin(callback: types.CallbackQuery) -> None:
    """Handle 'Skip this check-in' button press."""
    from datetime import datetime
    
    entry_type = callback.data.rsplit("_", 1)[1]

    user_id = callback.from_user.id
    today = date.today()

    # Create entry marked as skipped
    await upsert_entry(user_id, today, entry_type, {
        'skipped': True,
        'skipped_at': datetime.now().isoformat()
    })

    skip_messages = {
        'morning': (
            "✅ Morning check-in skipped.\n\n"
            "No worries! See you at your afternoon check-in. "
            "Have a great day! 😊"
        ),
        'day': (
            "✅ Day check-in skipped.\n\n"
            "That's okay! I'll catch up with you this evening. "
            "Keep up the good work! 💪"
        ),
        'evening': (
            "✅ Evening check-in skipped.\n\n"
            "Rest well! See you tomorrow morning for a fresh start. "
            "Good night! 🌙"
        )
    }

    await callback.answer()
    await callback.message.answer(
        skip_messages.get(entry_type, "✅ Check-in skipped."),
        reply_markup=remove_keyboard(),
        parse_mode="HTML"
    )

    logger.info(f"✅ Check-in skipped | user={user_id} | type={entry_type} | date={today}")