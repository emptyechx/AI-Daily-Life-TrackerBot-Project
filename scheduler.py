import logging
from typing import Optional
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from utils.constants import (
    PERIODS,
    REMINDER_MESSAGES,
    DEFAULT_MESSAGE,
    REMIND_LATER_INTERVAL,
    REMIND_LATER_MAX_COUNT
)

# ============================================================================
# SCHEDULER INITIALIZATION
# ============================================================================

scheduler = AsyncIOScheduler()
logger = logging.getLogger(__name__)

# Monitoring counters
_scheduler_stats = {
    'reminders_sent': 0,
    'reminders_failed': 0,
    'jobs_created': 0,
    'jobs_removed': 0,
    'last_cleanup': None
}


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

async def send_reminder(bot: Bot, user_id: int, period: str, remind_count: int = 0):
    """
    Send scheduled check-in reminder with dynamic keyboard.
    
    Args:
        bot: Bot instance
        user_id: Telegram user ID
        period: Check-in period ('morning', 'day', 'evening')
        remind_count: Number of times user clicked "Remind later"
    """
    try:
        from keyboards.builders import create_checkin_keyboard
        
        message_text = REMINDER_MESSAGES.get(period, DEFAULT_MESSAGE)
        
        # Add urgency message if this is a reminder
        if remind_count == 1:
            message_text += "\n\n⏰ <i>Friendly reminder!</i>"
        elif remind_count >= 2:
            message_text += "\n\n⚠️ <b>Last chance!</b> This is your final reminder."

        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            reply_markup=create_checkin_keyboard(period, remind_count),
            parse_mode="HTML"
        )

        # Update stats
        _scheduler_stats['reminders_sent'] += 1

        logger.info(
            f"✅ Reminder sent | user={user_id} | period={period} | "
            f"remind_count={remind_count}"
        )
        
    except TelegramAPIError as e:
        _scheduler_stats['reminders_failed'] += 1
        logger.error(
            f"❌ Telegram API error | user={user_id} | period={period} | error={e}",
            exc_info=True
        )
    except Exception as e:
        _scheduler_stats['reminders_failed'] += 1
        logger.error(
            f"❌ Unexpected error | user={user_id} | period={period} | error={e}",
            exc_info=True
        )


def _generate_job_id(user_id: int, period: str, is_onetime: bool = False) -> str:
    """
    Generate unique job ID for scheduler.

    """
    if is_onetime:
        timestamp = int(datetime.now().timestamp())
        return f"onetime_{user_id}_{period}_{timestamp}"
    return f"notif_{user_id}_{period}"


async def schedule_reminder(
    bot: Bot,
    user_id: int,
    time_str: str,
    period: str,
    timezone: str
) -> bool:
    """
    Schedule a recurring reminder.
    
    Args:
        bot: Bot instance
        user_id: Telegram user ID
        time_str: Time in HH:MM format
        period: Check-in period
        timezone: Timezone string
    
    Returns:
        True if scheduled successfully
    """
    try:
        parts = time_str.strip().split(':')
        if len(parts) < 2:
            logger.error(f"⚠️ Invalid time format | time={time_str} | user={user_id}")
            return False
            
        hour = int(parts[0])
        minute = int(parts[1])
        
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            logger.error(f"⚠️ Invalid hour/minute | time={time_str} | user={user_id}")
            return False

        job_id = _generate_job_id(user_id, period)

        scheduler.add_job(
            send_reminder,
            CronTrigger(hour=hour, minute=minute, timezone=timezone),
            args=[bot, user_id, period, 0],  # remind_count starts at 0
            id=job_id,
            replace_existing=True,
            misfire_grace_time=300
        )

        _scheduler_stats['jobs_created'] += 1

        logger.info(
            f"✅ Scheduled | user={user_id} | period={period} | "
            f"time={hour:02d}:{minute:02d} | tz={timezone}"
        )
        return True

    except ValueError as e:
        logger.error(f"⚠️ Value error | time={time_str} | user={user_id} | error={e}")
        return False
    except Exception as e:
        logger.error(
            f"❌ Scheduling failed | user={user_id} | period={period} | error={e}",
            exc_info=True
        )
        return False


async def schedule_onetime_reminder(
    bot: Bot,
    user_id: int,
    period: str,
    remind_count: int,
    delay_minutes: int = REMIND_LATER_INTERVAL
) -> Optional[str]:
    """
    Schedule a one-time reminder after a delay.

    Args:
        bot: Bot instance
        user_id: Telegram user ID
        period: Check-in period
        remind_count: Current remind count
        delay_minutes: Delay in minutes
    
    Returns:
        Job ID if scheduled, None if failed
    """
    try:
        run_time = datetime.now() + timedelta(minutes=delay_minutes)
        job_id = _generate_job_id(user_id, period, is_onetime=True)

        async def reminder_with_cleanup():
            """Wrapper to send reminder and clean up job."""
            await send_reminder(bot, user_id, period, remind_count)
            # Job is automatically removed after execution by APScheduler
            _scheduler_stats['jobs_removed'] += 1
            logger.debug(f"🧹 One-time job completed | job_id={job_id}")

        scheduler.add_job(
            reminder_with_cleanup,
            "date",
            run_date=run_time,
            id=job_id,
            replace_existing=False
        )

        _scheduler_stats['jobs_created'] += 1

        logger.info(
            f"✅ One-time reminder scheduled | user={user_id} | period={period} | "
            f"remind_count={remind_count} | run_at={run_time.strftime('%H:%M')}"
        )

        return job_id

    except Exception as e:
        logger.error(
            f"❌ One-time scheduling failed | user={user_id} | error={e}",
            exc_info=True
        )
        return None


async def schedule_user_notifications(
    bot: Bot,
    user_id: int,
    times: list[str],
    timezone: str
) -> int:
    """
    Schedule multiple daily reminders.
    
    Args:
        bot: Bot instance
        user_id: Telegram user ID
        times: List of times [morning, day, evening]
        timezone: Timezone string
    
    Returns:
        Number of successfully scheduled notifications
    """
    if len(times) != len(PERIODS):
        logger.warning(
            f"⚠️ Time count mismatch | user={user_id} | "
            f"expected={len(PERIODS)} | got={len(times)}"
        )

    scheduled_count = 0

    for i, time_str in enumerate(times):
        if i >= len(PERIODS):
            break

        period = PERIODS[i]
        success = await schedule_reminder(bot, user_id, time_str, period, timezone)

        if success:
            scheduled_count += 1

    logger.info(
        f"📅 User schedule complete | user={user_id} | "
        f"scheduled={scheduled_count}/{len(times)}"
    )

    return scheduled_count


def remove_user_schedule(user_id: int) -> int:
    """
    Remove all scheduled notifications for a user.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        Number of removed jobs
    """
    removed_count = 0

    for period in PERIODS:
        job_id = _generate_job_id(user_id, period)

        try:
            job = scheduler.get_job(job_id)
            if job:
                scheduler.remove_job(job_id)
                removed_count += 1
                _scheduler_stats['jobs_removed'] += 1
                logger.debug(f"🗑️ Removed job | job_id={job_id}")
        except JobLookupError:
            pass
        except Exception as e:
            logger.error(f"❌ Error removing job | job_id={job_id} | error={e}")

    if removed_count > 0:
        logger.info(f"🗑️ Removed schedule | user={user_id} | jobs={removed_count}")

    return removed_count


def get_user_schedule(user_id: int) -> dict[str, Optional[str]]:
    """
    Get current schedule for a user.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        Dictionary mapping period to scheduled time
    """
    schedule = {}

    for period in PERIODS:
        job_id = _generate_job_id(user_id, period)

        try:
            job = scheduler.get_job(job_id)
            if job and job.trigger:
                trigger = job.trigger
                try:
                    hour = trigger.fields[5].expressions[0].first
                    minute = trigger.fields[6].expressions[0].first
                    schedule[period] = f"{hour:02d}:{minute:02d}"
                except Exception:
                    schedule[period] = None
            else:
                schedule[period] = None
        except Exception as e:
            logger.error(f"❌ Error getting schedule | job_id={job_id} | error={e}")
            schedule[period] = None

    return schedule


async def reschedule_user_notifications(
    bot: Bot,
    user_id: int,
    times: list[str],
    timezone: str
) -> bool:
    """
    Update user notifications.
    
    Args:
        bot: Bot instance
        user_id: Telegram user ID
        times: New notification times
        timezone: Timezone string
    
    Returns:
        True if successful
    """
    remove_user_schedule(user_id)
    scheduled_count = await schedule_user_notifications(bot, user_id, times, timezone)

    success = scheduled_count == len(times)

    if success:
        logger.info(f"✅ Rescheduled | user={user_id}")
    else:
        logger.warning(
            f"⚠️ Partial reschedule | user={user_id} | "
            f"scheduled={scheduled_count}/{len(times)}"
        )

    return success


async def cleanup_old_jobs():
    """
    Removes completed one-time jobs older than 24 hours.
    """
    try:
        all_jobs = scheduler.get_jobs()
        removed = 0
        
        current_time = datetime.now()
        
        for job in all_jobs:
            # Only process one-time jobs
            if not job.id.startswith('onetime_'):
                continue
            
            # Check if job is old (no next_run_time means it's done)
            if job.next_run_time is None:
                scheduler.remove_job(job.id)
                removed += 1
            # Also remove if scheduled time was more than 24 hours ago
            elif job.next_run_time < current_time - timedelta(hours=24):
                scheduler.remove_job(job.id)
                removed += 1
        
        if removed > 0:
            _scheduler_stats['jobs_removed'] += removed
            logger.info(f"🧹 Cleanup complete | removed_jobs={removed}")
        
        _scheduler_stats['last_cleanup'] = datetime.now()
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed | error={e}", exc_info=True)


async def start_scheduler(bot: Bot):
    """
    Start the notification scheduler with monitoring.

    """
    if not scheduler.running:
        try:
            scheduler.start()
            
            # Schedule periodic cleanup
            scheduler.add_job(
                cleanup_old_jobs,
                "interval",
                hours=6,  # Run every 6 hours
                id="cleanup_old_jobs",
                replace_existing=True
            )
            
            logger.info("✅ APScheduler started successfully")
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler | error={e}", exc_info=True)
            raise
    else:
        logger.warning("⚠️ Scheduler is already running")


async def stop_scheduler():
    """Stop the scheduler gracefully."""
    if scheduler.running:
        try:
            scheduler.shutdown(wait=True)
            logger.info("✅ APScheduler stopped successfully")
        except Exception as e:
            logger.error(f"❌ Error stopping scheduler | error={e}", exc_info=True)
    else:
        logger.warning("⚠️ Scheduler is not running")


def is_scheduler_running() -> bool:
    """Check if scheduler is running."""
    return scheduler.running


def get_scheduler_status() -> dict:
    """
    Get current scheduler status and statistics.
        
    Returns:
        Dictionary with scheduler status and statistics
    """
    jobs = scheduler.get_jobs()
    
    # Categorize jobs
    recurring_jobs = [j for j in jobs if not j.id.startswith('onetime_')]
    onetime_jobs = [j for j in jobs if j.id.startswith('onetime_')]
    
    return {
        "running": scheduler.running,
        "total_jobs": len(jobs),
        "recurring_jobs": len(recurring_jobs),
        "onetime_jobs": len(onetime_jobs),
        "state": scheduler.state,
        "stats": _scheduler_stats.copy()
    }


def reset_scheduler_stats():
    """Reset monitoring statistics."""
    global _scheduler_stats
    _scheduler_stats = {
        'reminders_sent': 0,
        'reminders_failed': 0,
        'jobs_created': 0,
        'jobs_removed': 0,
        'last_cleanup': _scheduler_stats.get('last_cleanup')
    }
    logger.info("📊 Scheduler stats reset")