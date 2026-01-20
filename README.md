# 🤖 AI Daily Life Tracker Bot

A Telegram bot that helps users track their daily mood, energy, sleep patterns, and habits using AI-powered insights.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![aiogram](https://img.shields.io/badge/aiogram-3.x-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 📋 Overview

This bot provides:
- **3 Daily Check-ins**: Morning, afternoon, and evening tracking
- **AI-Powered Insights**: Weekly summaries with personalized recommendations
- **Habit Tracking**: Monitor water intake, exercise, meditation, and medication
- **Smart Scheduling**: Automated reminders based on your sleep schedule
- **Pattern Analysis**: Discover correlations between your habits and well-being

## ✨ Features

### Core Functionality
- 🌅 **Morning Check-in**: Track sleep quality, mood, and energy levels
- ☀️ **Day Check-in**: Monitor midday mood, energy, and stress
- 🌙 **Evening Check-in**: Reflect on daily satisfaction and overall well-being

### AI Features
- 📊 **Weekly Reports**: AI-generated insights based on your patterns
- 🔍 **Pattern Recognition**: Identifies correlations between habits and mood
- 💡 **Personalized Tips**: Actionable recommendations for improvement
- 🏷️ **Smart Tagging**: Automatically categorizes your notes and reflections

### User Experience
- ⚙️ **Flexible Scheduling**: Custom or default notification times
- 🌍 **Timezone Support**: Automatic timezone detection and validation
- 📝 **Profile Management**: Easy editing of all profile settings
- 🔄 **Smart Reminders**: "Remind me later" option with intelligent limits

## 🛠️ Tech Stack

- **Framework**: [aiogram 3.x](https://docs.aiogram.dev/) - Modern Telegram Bot API
- **Database**: [Supabase](https://supabase.com/) - PostgreSQL with real-time capabilities
- **AI**: [Google Gemini 2.5 Flash](https://ai.google.dev/) - Fast AI for insights
- **Scheduler**: [APScheduler](https://apscheduler.readthedocs.io/) - Job scheduling
- **Python**: 3.11+ with async/await patterns

## 📁 Project Structure

```
.
├── bot.py                 # Main entry point
├── config.py              # Configuration management
├── scheduler.py           # Notification scheduling
├── handlers/              # Telegram command handlers
│   ├── commands.py        # Basic bot commands
│   ├── registration.py    # User registration flow
│   ├── morning_checkin.py # Morning check-in logic
│   ├── day_checkin.py     # Day check-in logic
│   ├── evening_checkin.py # Evening check-in logic
│   ├── notification.py    # Notification handlers
│   ├── edit_profile.py    # Profile editing
│   └── states.py          # FSM state definitions
├── keyboards/             # Keyboard builders
│   └── builders.py        # Reply & inline keyboards
├── database/              # Database operations
│   ├── supabase_db.py     # Profile management
│   ├── daily_entries_db.py # Entry operations
│   └── weekly_summary_db.py # Weekly statistics
├── ai/                    # AI integration
│   ├── gemini_client.py   # Gemini configuration
│   ├── gemini_service.py  # AI services
│   └── quick_responses.py # Fast AI responses
├── utils/                 # Utility functions
│   ├── constants.py       # App constants
│   ├── validators.py      # Input validation
│   ├── cache.py           # Caching system
│   ├── error_recovery.py  # Error handling
│   ├── text_analyzer.py   # NLP utilities
│   └── text_formatter.py  # Text formatting
└── tests/                 # Unit tests
    └── test_validators.py # Validator tests
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- PostgreSQL database (via Supabase)
- Telegram Bot Token
- Google Gemini API Key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai-life-tracker-bot.git
   cd ai-life-tracker-bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Set up database**
   - Create a Supabase project at https://supabase.com
   - Run the SQL schema from `database/schema.sql`
   - Copy your Supabase URL and API key to `.env`

6. **Run the bot**
   ```bash
   python bot.py
   ```

## 📝 Environment Variables

See `.env.example` for required configuration:

```env
BOT_TOKEN=your_telegram_bot_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
GEMINI_API_KEY=your_gemini_api_key
```

## 🧪 Testing

Run unit tests:
```bash
pytest tests/
```

Run specific test file:
```bash
pytest tests/test_validators.py -v
```

## 📖 User Guide

### Registration
1. Start the bot: `/start`
2. Click "Create Profile"
3. Follow the guided setup:
   - Enter basic info (age, gender, height, weight)
   - Set sleep schedule
   - Choose notification times
   - Select habits to track

### Daily Usage
- **Morning**: `/morning` or wait for automated reminder
- **Afternoon**: `/day` or wait for automated reminder
- **Evening**: `/evening` or wait for automated reminder

### Commands
- `/start` - Start the bot or return to menu
- `/my_profile` - View your profile
- `/weekly_report` - Get AI insights for the week
- `/history` - View past weekly summaries
- `/edit_profile` - Modify your profile settings
- `/jobs` - Check scheduled notifications
- `/reload_schedule` - Refresh notification timers
- `/delete_profile` - Delete all data
- `/help` - Show help message

## 🏗️ Architecture

### Async Patterns
The bot uses Python's async/await throughout for efficient handling of concurrent users:
```python
# All database operations use asyncio.to_thread
response = await asyncio.to_thread(
    lambda: client.table("profiles").select("*").execute()
)
```

### State Management
User conversations are managed with aiogram's Finite State Machine (FSM):
```python
class Registration(StatesGroup):
    gender = State()
    age = State()
    height = State()
    # ... more states
```

### Caching
Expensive operations are cached in-memory:
```python
@cache_async(ttl=3600)
async def calculate_weekly_stats(user_id, week_start):
    # ... expensive computation
```

### Error Handling
Decorator pattern for consistent error handling:
```python
@handle_db_errors(default_return=None)
async def get_user_profile(telegram_id: int):
    # ... database operation
```

## 🔒 Privacy & Security

- User data is stored securely in PostgreSQL
- All sensitive data transmitted over HTTPS
- No data sharing with third parties
- AI analysis happens server-side only
- Users can delete all data anytime with `/delete_profile`

## 🤝 Contributing

This is a personal learning project, but suggestions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- [aiogram](https://github.com/aiogram/aiogram) - Excellent Telegram Bot framework
- [Supabase](https://supabase.com/) - Backend as a Service
- [Google Gemini](https://ai.google.dev/) - AI capabilities
- [APScheduler](https://github.com/agronholm/apscheduler) - Job scheduling

## 📧 Contact

**Author**: Bohdan Hvozdynskyi 
**Email**: hvozdynskyi.bohdan@gmail.com
**Telegram**: @emptyechx

---

**Note**: This is an educational project. It demonstrates practical skills in Python, async programming, database design, API integration, and user experience design.

## 🎯 Learning Outcomes

This project helped me learn:
- ✅ Modern async/await patterns in Python
- ✅ Telegram Bot API and conversational UI design
- ✅ PostgreSQL database design and operations
- ✅ AI integration with Google Gemini
- ✅ State management with FSM
- ✅ Error handling and logging
- ✅ Job scheduling and background tasks
- ✅ Input validation and security practices
- ✅ Code organization and architecture
- ✅ Git workflow and version control

---

Made with ❤️ for learning and growth