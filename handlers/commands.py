import logging
from datetime import date, timedelta
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.supabase_db import get_user_profile, delete_user_profile
from database.weekly_summary_db import calculate_weekly_stats, get_user_summaries
from database.daily_entries_db import get_weekly_entries
from keyboards.builders import create_main_menu_keyboard, remove_keyboard
from utils.validators import escape_html
from scheduler import (
    schedule_user_notifications,
    remove_user_schedule,
    send_reminder,
    get_user_schedule,
    scheduler
)

router = Router()
logger = logging.getLogger(__name__)

WELCOME_TEXT_NEW_USER = (
    "🤖 <b>AI Daily Life Tracker</b> — your personal analyst.\n\n"
    "🎯 <b>Our goal:</b> Eliminate chaos and reveal how sleep, stress, mood"
    "and habits affect your well-being.\n\n"
    "🚀 <b>Key Features:</b>\n"
    "✅ <b>Deep Analytics:</b> AI patterns recognition.\n"
    "✅ <b>Personal Insights:</b> Conclusions based on your data.\n"
    "✅ <b>Easy Tracking:</b> Log mood and habits in under 2 min.\n\n"
    "🔐 <b>Privacy:</b> Data is encrypted and NOT used for training global models.\n\n"
    "To begin, let's set up your profile!"
)

WELCOME_TEXT_EXISTING_USER = (
    "👋 Welcome back, <b>{name}</b>! I'm tracking your data.\n"
    " Ready for another insightful day? 😊\n"
    " Use the /help command to see what I can do."
)

HELP_TEXT = (
    "🤖 <b>AI Tracker Help</b>\n\n"
    "• /start — Restart or register\n"
    "• /my_profile — Show my data\n"
    "• /weekly_report — This week's progress + AI insights\n"
    "• /history — View past summaries\n"
    "• /jobs — Check my schedule\n"
    "• /reload_schedule — Refresh timers\n"
    "• /edit_profile — Edit my profile\n"
    "• /delete_profile — Delete all data\n"
    "• /help — Show this message\n\n"
    "Need more help? Contact support."
)

DELETE_CONFIRMATION_TEXT = (
    "⚠️ <b>WARNING!</b>\n\n"
    "This action cannot be undone. All your data will be <b>completely deleted</b>.\n\n"
    "Are you sure?"
)

MSG_NO_PROFILE = "❌ No profile found! Use /start to create one."
MSG_PROFILE_DELETED = "🧹 <b>All your data has been deleted.</b> Goodbye!"
MSG_DELETE_CANCELLED = "Happy to see you stay! 😊"
MSG_DELETE_ERROR = "❌ Error deleting profile. Please try again later."
MSG_SCHEDULE_UPDATED = "🔄 <b>Schedule updated successfully!</b>"
MSG_TEST_SENT = "✅ <b>Test notification sent!</b> Check your messages."
MSG_NO_JOBS = "📅 <b>No scheduled jobs found!</b>"


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    user_id = message.from_user.id
    user_profile = await get_user_profile(user_id)

    if user_profile:
        name = user_profile.get('first_name') or message.from_user.first_name
        await message.answer(
            WELCOME_TEXT_EXISTING_USER.format(name=name),
            reply_markup=remove_keyboard(),
            parse_mode=ParseMode.HTML
        )
        logger.info(f"User {user_id} ({name}) returned")
    else:
        await message.answer(
            WELCOME_TEXT_NEW_USER,
            reply_markup=create_main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
        logger.info(f"New user {user_id} started bot")


@router.message(Command("my_profile"))
async def cmd_my_profile(message: types.Message) -> None:
    profile = await get_user_profile(message.from_user.id)

    if not profile:
        return await message.answer(MSG_NO_PROFILE)

    name = profile.get('first_name', 'N/A')
    gender = profile.get('gender', 'N/A')
    age = profile.get('age', 'N/A')
    height = profile.get('height', 'N/A')
    weight = profile.get('weight', 'N/A')
    activity = profile.get('activity_level', 'N/A')
    bedtime = profile.get('bedtime_usual', 'N/A')
    wakeup = profile.get('wakeuptime_usual', 'N/A')
    timezone = profile.get('timezone', 'UTC')
    habits = ", ".join(profile.get('habits', [])) or "None"
    notification_times = ", ".join(profile.get('notification_times', [])) or "Not set"

    profile_card = (
        f"👤 <b>Profile:</b> {escape_html(name)}\n\n"
        f"📊 <b>Stats:</b> {escape_html(gender)}, {escape_html(age)} y.o, {escape_html(height)}cm, {escape_html(weight)}kg\n"
        f"🏃 <b>Activity:</b> {escape_html(activity)}\n"
        f"😴 <b>Sleep:</b> {escape_html(bedtime)} - {escape_html(wakeup)}\n"
        f"🛠 <b>Trackers:</b> {escape_html(habits)}\n"
        f"📲 <b>Notifications:</b> {escape_html(notification_times)}\n"
        f"🌍 <b>Timezone:</b> {escape_html(timezone)}\n\n"
    )

    await message.answer(profile_card, parse_mode=ParseMode.HTML)
    logger.info(f"Profile viewed by user {message.from_user.id}")


@router.message(Command("weekly_report"))
async def cmd_weekly_report(message: types.Message) -> None:
    """Show current week's progress with AI insights."""
    user_id = message.from_user.id
    profile = await get_user_profile(user_id)
    
    if not profile:
        return await message.answer(MSG_NO_PROFILE)
    
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    
    # Get stats
    stats = await calculate_weekly_stats(user_id, week_start)
    
    if not stats or stats.get('total_checkins', 0) == 0:
        return await message.answer(
            "📊 <b>This Week's Report</b>\n\n"
            "No check-ins completed yet this week.\n"
            "Start tracking to see your progress!",
            parse_mode=ParseMode.HTML
        )
    
    # Show loading message for AI
    loading_msg = await message.answer("🤖 Analyzing your week with AI...")
    
    # Get entries for AI analysis
    entries = await get_weekly_entries(user_id, week_start)
    
    # Try to generate AI insights
    ai_insights = None
    try:
        from ai.gemini_service import generate_weekly_insights, is_ai_available
        
        if is_ai_available():
            ai_insights = await generate_weekly_insights(profile, entries)
    except Exception as e:
        logger.error(f"AI insights error: {e}")
    
    # Format report
    completed_days = stats.get('completed_days', 0)
    total_checkins = stats.get('total_checkins', 0)
    morning_count = stats.get('morning_count', 0)
    day_count = stats.get('day_count', 0)
    evening_count = stats.get('evening_count', 0)
    
    days_in_week = (today - week_start).days + 1
    completion_pct = int((completed_days / days_in_week) * 100) if days_in_week > 0 else 0
    
    report = (
        f"📊 <b>This Week's Report</b>\n"
        f"Week: {week_start.strftime('%b %d')} - {today.strftime('%b %d')}\n\n"
        f"✅ <b>Completion:</b> {completed_days}/{days_in_week} days ({completion_pct}%)\n"
        f"📈 <b>Total Check-ins:</b> {total_checkins}\n"
        f"🌅 Morning: {morning_count}\n"
        f"☀️ Day: {day_count}\n"
        f"🌙 Evening: {evening_count}\n\n"
    )
    
    # Add averages
    if stats.get('avg_mood') is not None:
        mood_emoji = "😊" if stats['avg_mood'] >= 4 else "😐" if stats['avg_mood'] >= 3 else "😔"
        report += f"{mood_emoji} <b>Avg Mood:</b> {stats['avg_mood']}/5\n"
    
    if stats.get('avg_energy') is not None:
        energy_emoji = "⚡" if stats['avg_energy'] >= 4 else "🔋" if stats['avg_energy'] >= 3 else "🪫"
        report += f"{energy_emoji} <b>Avg Energy:</b> {stats['avg_energy']}/5\n"
    
    if stats.get('avg_stress') is not None:
        stress_emoji = "😰" if stats['avg_stress'] >= 4 else "😐" if stats['avg_stress'] >= 3 else "😌"
        report += f"{stress_emoji} <b>Avg Stress:</b> {stats['avg_stress']}/5\n"
    
    if stats.get('avg_sleep_quality') is not None:
        sleep_emoji = "💤" if stats['avg_sleep_quality'] >= 4 else "😴" if stats['avg_sleep_quality'] >= 3 else "😵"
        report += f"{sleep_emoji} <b>Avg Sleep:</b> {stats['avg_sleep_quality']}/5\n"
    
    # Add AI insights if available
    if ai_insights and ai_insights.get('summary'):
        report += f"\n🤖 <b>AI Insights:</b>\n<i>{ai_insights['summary']}</i>\n\n"
        report += f"💡 <b>Recommendations:</b>\n{ai_insights['recommendations']}\n"
    else:
        report += "\n💪 Keep up the great work!"
    
    # Delete loading message
    await loading_msg.delete()
    
    await message.answer(report, parse_mode=ParseMode.HTML)
    logger.info(f"Weekly report viewed by user {user_id}")


@router.message(Command("history"))
async def cmd_history(message: types.Message) -> None:
    """Show past weekly summaries."""
    user_id = message.from_user.id
    profile = await get_user_profile(user_id)
    
    if not profile:
        return await message.answer(MSG_NO_PROFILE)
    
    summaries = await get_user_summaries(user_id, limit=5)
    
    if not summaries:
        return await message.answer(
            "📚 <b>History</b>\n\n"
            "No weekly summaries available yet.\n"
            "Complete a full week to generate your first summary!",
            parse_mode=ParseMode.HTML
        )
    
    history_text = "📚 <b>Your Weekly Summaries</b>\n\n"
    
    for summary in summaries:
        week_start = summary.get('week_start_date', 'Unknown')
        completed_days = summary.get('completed_days', 0)
        avg_mood = summary.get('avg_mood')
        
        mood_emoji = "😊" if avg_mood and avg_mood >= 4 else "😐" if avg_mood and avg_mood >= 3 else "😔"
        
        history_text += (
            f"📅 Week of {week_start}\n"
            f"   ✅ {completed_days}/7 days\n"
        )
        
        if avg_mood:
            history_text += f"   {mood_emoji} Mood: {avg_mood}/5\n"
        
        history_text += "\n"
    
    await message.answer(history_text, parse_mode=ParseMode.HTML)
    logger.info(f"History viewed by user {user_id}")


@router.message(Command("jobs"))
async def cmd_jobs(message: types.Message) -> None:
    user_id = message.from_user.id
    user_profile = await get_user_profile(user_id)

    if not user_profile:
        return await message.answer(MSG_NO_PROFILE)

    user_jobs = [
        job for job in scheduler.get_jobs()
        if str(user_id) in job.id
    ]

    if not user_jobs:
        return await message.answer(MSG_NO_JOBS, parse_mode=ParseMode.HTML)

    jobs_text = "📅 <b>Your active schedule:</b>\n\n"
    for job in user_jobs:
        job_parts = job.id.split('_')
        job_type = job_parts[-1].capitalize() if len(job_parts) > 2 else "Unknown"

        next_run = job.next_run_time.strftime("%H:%M (%d %b)") if job.next_run_time else "Not scheduled"

        jobs_text += f"• <b>{job_type}</b>: next run at <code>{next_run}</code>\n"

    await message.answer(jobs_text, parse_mode=ParseMode.HTML)
    logger.info(f"Schedule viewed by user {user_id}")


@router.message(Command("reload_schedule"))
async def cmd_reload_schedule(message: types.Message, bot: Bot) -> None:
    user_id = message.from_user.id
    user_profile = await get_user_profile(user_id)

    if not user_profile:
        return await message.answer(MSG_NO_PROFILE)

    try:
        scheduled_count = await schedule_user_notifications(
            bot,
            user_id,
            user_profile.get('notification_times', []),
            user_profile.get('timezone', 'UTC')
        )

        await message.answer(
            MSG_SCHEDULE_UPDATED,
            parse_mode=ParseMode.HTML
        )
        logger.info(f"Schedule reloaded for user {user_id}: {scheduled_count} jobs")

    except Exception as e:
        logger.error(f"Error reloading schedule for {user_id}: {e}")
        await message.answer(
            "❌ Error updating schedule. Please try again.",
            parse_mode=ParseMode.HTML
        )


@router.message(Command("delete_profile"))
async def cmd_delete_confirm(message: types.Message) -> None:
    user_id = message.from_user.id
    user_profile = await get_user_profile(user_id)

    if not user_profile:
        return await message.answer(MSG_NO_PROFILE)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="❌ YES, delete all",
            callback_data="confirm_delete_all"
        )],
        [InlineKeyboardButton(
            text="✅ No, keep my data",
            callback_data="cancel_delete"
        )]
    ])

    await message.answer(
        DELETE_CONFIRMATION_TEXT,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    logger.info(f"Delete confirmation shown to user {user_id}")


@router.callback_query(F.data == "confirm_delete_all")
async def process_delete_profile(callback: types.CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id

    try:
        success = await delete_user_profile(user_id)

        if success:
            removed_count = remove_user_schedule(user_id)

            await state.clear()

            await callback.message.edit_text(
                MSG_PROFILE_DELETED,
                parse_mode=ParseMode.HTML
            )

            logger.info(
                f"Profile deleted for user {user_id}. "
                f"Removed {removed_count} scheduled jobs."
            )
        else:
            await callback.answer(MSG_DELETE_ERROR, show_alert=True)
            logger.error(f"Failed to delete profile for user {user_id}")

    except Exception as e:
        logger.error(f"Error deleting profile for {user_id}: {e}", exc_info=True)
        await callback.answer(MSG_DELETE_ERROR, show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: types.CallbackQuery) -> None:
    await callback.message.edit_text(MSG_DELETE_CANCELLED)
    await callback.answer()
    logger.info(f"Delete cancelled by user {callback.from_user.id}")


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    await message.answer(HELP_TEXT, parse_mode=ParseMode.HTML)
    logger.info(f"Help viewed by user {message.from_user.id}")


@router.message(F.text == "Later")
async def handle_later(message: types.Message) -> None:
    await message.answer(
        "No problem! When you're ready, just use /start to begin.",
        reply_markup=remove_keyboard()
    )
    logger.info(f"User {message.from_user.id} chose 'Later'")