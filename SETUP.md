# 🛠️ Setup Guide

Complete guide to setting up the AI Daily Life Tracker Bot from scratch.

## 📋 Prerequisites

Before you begin, ensure you have:

- ✅ Python 3.11 or higher installed
- ✅ Git installed
- ✅ A Telegram account
- ✅ Internet connection

## 🚀 Step 1: Create Telegram Bot

1. **Open Telegram** and search for `@BotFather`

2. **Start a chat** and send `/newbot`

3. **Follow the prompts:**
   - Choose a name for your bot (e.g., "My Life Tracker")
   - Choose a username (must end in 'bot', e.g., "my_life_tracker_bot")

4. **Save your bot token!** It looks like:
   ```
   1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

5. **Configure bot settings:**
   ```
   /setcommands
   ```
   Then paste:
   ```
   start - Start the bot
   my_profile - View profile
   weekly_report - Get AI insights
   edit_profile - Edit profile
   help - Show help
   ```

## 🗄️ Step 2: Set Up Supabase Database

### 2.1 Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Sign up / Log in
3. Click "New Project"
4. Fill in:
   - **Name**: AI Life Tracker
   - **Database Password**: (choose a strong password)
   - **Region**: Choose closest to you
5. Wait for project to initialize (~2 minutes)

### 2.2 Create Database Tables

1. In Supabase Dashboard, go to **SQL Editor**

2. Click **New Query**

3. **Copy and paste this schema:**

```sql
-- ============================================================================
-- PROFILES TABLE
-- ============================================================================

CREATE TABLE profiles (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    gender TEXT NOT NULL,
    age INTEGER NOT NULL,
    height NUMERIC(5,2) NOT NULL,
    weight NUMERIC(5,2) NOT NULL,
    activity_level TEXT NOT NULL,
    bedtime_usual TEXT NOT NULL,
    wakeuptime_usual TEXT NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    habits TEXT[] DEFAULT '{}',
    use_default_notifications BOOLEAN DEFAULT TRUE,
    notification_times TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX idx_profiles_telegram_id ON profiles(telegram_id);


-- ============================================================================
-- ENTRIES TABLE (Daily Check-ins)
-- ============================================================================

CREATE TABLE entries (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    entry_date DATE NOT NULL,
    entry_type TEXT NOT NULL, -- 'morning', 'day', 'evening'
    
    -- Ratings
    sleep_quality INTEGER CHECK (sleep_quality >= 1 AND sleep_quality <= 5),
    mood INTEGER CHECK (mood >= 1 AND mood <= 5),
    energy INTEGER CHECK (energy >= 1 AND energy <= 5),
    stress INTEGER CHECK (stress >= 1 AND stress <= 5),
    
    -- Boolean fields
    wakeup_on_time BOOLEAN,
    daily_satisfaction BOOLEAN,
    
    -- Text fields
    actual_wakeup_time TEXT,
    conditional_question TEXT,
    conditional_answer TEXT,
    user_notes TEXT,
    day_reflection TEXT,
    
    -- Tags (automatically extracted)
    tags TEXT[] DEFAULT '{}',
    
    -- Completion tracking
    completed_at TIMESTAMP WITH TIME ZONE,
    skipped BOOLEAN DEFAULT FALSE,
    skipped_at TIMESTAMP WITH TIME ZONE,
    
    -- Reminder tracking
    remind_later_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure one entry per user per date per type
    UNIQUE(telegram_id, entry_date, entry_type)
);

-- Indexes for fast queries
CREATE INDEX idx_entries_telegram_id ON entries(telegram_id);
CREATE INDEX idx_entries_date ON entries(entry_date);
CREATE INDEX idx_entries_type ON entries(entry_type);
CREATE INDEX idx_entries_completed ON entries(completed_at);


-- ============================================================================
-- WEEKLY SUMMARIES TABLE
-- ============================================================================

CREATE TABLE weekly_summaries (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    week_start_date DATE NOT NULL,
    week_end_date DATE NOT NULL,
    
    -- Statistics
    total_checkins INTEGER DEFAULT 0,
    completed_days INTEGER DEFAULT 0,
    morning_count INTEGER DEFAULT 0,
    day_count INTEGER DEFAULT 0,
    evening_count INTEGER DEFAULT 0,
    
    -- Averages
    avg_mood NUMERIC(3,2),
    avg_energy NUMERIC(3,2),
    avg_stress NUMERIC(3,2),
    avg_sleep_quality NUMERIC(3,2),
    
    -- AI insights
    ai_summary TEXT,
    ai_recommendations TEXT,
    
    -- Top patterns
    top_stressors TEXT[] DEFAULT '{}',
    top_activities TEXT[] DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(telegram_id, week_start_date)
);

-- Index for fast queries
CREATE INDEX idx_summaries_telegram_id ON weekly_summaries(telegram_id);
CREATE INDEX idx_summaries_week ON weekly_summaries(week_start_date);


-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_entries_updated_at BEFORE UPDATE ON entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_summaries_updated_at BEFORE UPDATE ON weekly_summaries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- ROW LEVEL SECURITY (RLS) - Optional but Recommended
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_summaries ENABLE ROW LEVEL SECURITY;

-- Allow service role to do everything (for your bot)
CREATE POLICY "Service role can do everything" ON profiles
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can do everything" ON entries
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can do everything" ON weekly_summaries
    FOR ALL USING (auth.role() = 'service_role');
```

4. Click **Run** (or press Ctrl+Enter)

5. **Verify tables were created:**
   - Go to **Table Editor** in sidebar
   - You should see: `profiles`, `entries`, `weekly_summaries`

### 2.3 Get Supabase Credentials

1. Go to **Settings** > **API**

2. **Copy these values:**
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon/public key**: `eyJhbGc...` (long string)

3. Save them for later!

## 🤖 Step 3: Get Google Gemini API Key

1. Go to [ai.google.dev](https://ai.google.dev/)

2. Click **Get API Key** (top right)

3. Sign in with Google account

4. Click **Create API Key**

5. **Copy the key** - looks like: `AIzaSyXXXXXXXXXXXXXXXXXXXXXX`

6. **Note:** Free tier includes:
   - 60 requests per minute
   - Plenty for personal use!

## 💻 Step 4: Set Up Local Development

### 4.1 Clone the Repository

```bash
# Clone your repo (or download ZIP)
git clone https://github.com/emptyechx/ai-life-tracker-bot.git
cd ai-life-tracker-bot
```

### 4.2 Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal.

### 4.3 Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- aiogram (Telegram Bot framework)
- supabase (Database client)
- google-generativeai (Gemini AI)
- APScheduler (Job scheduling)
- And other dependencies

### 4.4 Configure Environment Variables

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your credentials:**
   ```bash
   # Use your favorite editor
   nano .env
   # or
   code .env
   # or
   notepad .env
   ```

3. **Fill in your values:**
   ```env
   BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_KEY=eyJhbGc...
   GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXX
   ```

4. **Save the file!**

## ✅ Step 5: Test the Setup

### 5.1 Verify Configuration

```bash
python -c "from config import get_bot_token; print('✅ Config loaded')"
```

Should print: `✅ Config loaded`

### 5.2 Test Database Connection

```bash
python -c "from database.supabase_db import get_supabase; print('✅ Database connected')"
```

Should print: `✅ Database connected`

### 5.3 Run Tests

```bash
pytest tests/ -v
```

Should see all tests passing! ✅

### 5.4 Start the Bot

```bash
python bot.py
```

**Expected output:**
```
2025-01-08 12:00:00 - INFO - Initializing bot...
2025-01-08 12:00:00 - INFO - Scheduler started successfully
2025-01-08 12:00:00 - INFO - ✅ Gemini AI initialized
2025-01-08 12:00:00 - INFO - Bot startup complete
2025-01-08 12:00:00 - INFO - Starting polling...
```

## 🎉 Step 6: Test Your Bot

1. **Open Telegram** and find your bot

2. **Send `/start`**

3. **Complete registration:**
   - Enter your info
   - Choose notification times
   - Save profile

4. **Try commands:**
   - `/my_profile` - View your profile
   - `/morning` - Do a morning check-in
   - `/help` - See all commands

## 🐛 Troubleshooting

### Bot doesn't respond

**Check:**
- Bot is running (`python bot.py`)
- Token is correct in `.env`
- No error messages in terminal

**Fix:**
```bash
# Restart the bot
Ctrl+C  # Stop
python bot.py  # Start again
```

### Database errors

**Check:**
- Supabase URL is correct
- Supabase key is correct (use `anon` key, not `service` key)
- Tables were created (check Table Editor)

**Fix:**
```bash
# Re-run the schema SQL in Supabase SQL Editor
```

### Import errors

**Check:**
- Virtual environment is activated (see `(venv)` in terminal)
- All dependencies installed

**Fix:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Timezone errors

**Check:**
- `pytz` is installed

**Fix:**
```bash
pip install pytz --upgrade
```

## 🚀 Next Steps

### For Development:

1. **Enable debug logging:**
   ```python
   # In bot.py
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Use test database:**
   - Create separate Supabase project for testing
   - Use different `.env` file

3. **Set up Git:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

### For Production:

1. **Use environment variables** instead of `.env` file

2. **Set up monitoring:**
   - Error tracking (Sentry)
   - Uptime monitoring

3. **Deploy to server:**
   - VPS (DigitalOcean, AWS)
   - Or use serverless (Heroku, Railway)

4. **Set up backups:**
   - Supabase has automatic backups
   - Export data regularly

## 📚 Resources

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [aiogram Documentation](https://docs.aiogram.dev/)
- [Supabase Documentation](https://supabase.com/docs)
- [Google Gemini API](https://ai.google.dev/docs)
- [Python Async/Await](https://realpython.com/async-io-python/)

## 💬 Support

Having issues? Check:
1. Error messages in terminal
2. Supabase logs (Dashboard > Logs)
3. Make sure all credentials are correct
4. Verify virtual environment is activated

## ✅ Setup Checklist

- [ ] Telegram bot created and token saved
- [ ] Supabase project created
- [ ] Database tables created
- [ ] Gemini API key obtained
- [ ] Repository cloned
- [ ] Virtual environment created and activated
- [ ] Dependencies installed
- [ ] `.env` file configured
- [ ] Tests passing
- [ ] Bot running successfully
- [ ] First user registered

**Congratulations! Your bot is ready to use!** 🎉