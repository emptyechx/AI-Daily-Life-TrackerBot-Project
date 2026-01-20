"""
Setup Verification Script
Run this after setup to verify everything is configured correctly.

Usage: python verify_setup.py
"""

import sys
import os
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def check_mark(success):
    """Return checkmark or X."""
    return "✅" if success else "❌"


def check_file_exists(filepath, required=True):
    """Check if a file exists."""
    exists = Path(filepath).exists()
    status = check_mark(exists)
    req_text = "(required)" if required else "(optional)"
    print(f"{status} {filepath} {req_text}")
    return exists


def check_env_variables():
    """Check if required environment variables are set."""
    print_header("Checking Environment Variables")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("❌ python-dotenv not installed")
        return False
    
    required_vars = [
        "BOT_TOKEN",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "GEMINI_API_KEY"
    ]
    
    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        is_set = value is not None and len(value) > 0
        status = check_mark(is_set)
        
        if is_set:
            # Show first/last 4 chars for security
            masked = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
            print(f"{status} {var}: {masked}")
        else:
            print(f"{status} {var}: NOT SET")
            all_set = False
    
    return all_set


def check_dependencies():
    """Check if required packages are installed."""
    print_header("Checking Dependencies")
    
    packages = [
        ("aiogram", "Telegram Bot framework"),
        ("supabase", "Database client"),
        ("google.generativeai", "AI service"),
        ("apscheduler", "Job scheduler"),
        ("pytz", "Timezone support"),
        ("pytest", "Testing framework (optional)"),
    ]
    
    all_installed = True
    for package_name, description in packages:
        try:
            __import__(package_name)
            print(f"✅ {package_name}: {description}")
        except ImportError:
            print(f"❌ {package_name}: {description} - NOT INSTALLED")
            if package_name != "pytest":  # pytest is optional
                all_installed = False
    
    return all_installed


def check_database_connection():
    """Check if database connection works."""
    print_header("Checking Database Connection")
    
    try:
        from database.supabase_db import get_supabase
        client = get_supabase()
        
        # Try a simple query
        response = client.table("profiles").select("count").execute()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def check_ai_service():
    """Check if AI service is available."""
    print_header("Checking AI Service")
    
    try:
        from ai.gemini_client import is_ai_available, configure_gemini
        
        configure_gemini()
        
        if is_ai_available():
            print("✅ Gemini AI configured successfully")
            return True
        else:
            print("❌ Gemini AI not available")
            return False
    except Exception as e:
        print(f"❌ Gemini AI configuration failed: {e}")
        return False


def check_file_structure():
    """Check if all required files exist."""
    print_header("Checking File Structure")
    
    required_files = [
        "bot.py",
        "config.py",
        "scheduler.py",
        ".env",
        "requirements.txt",
    ]
    
    recommended_files = [
        "README.md",
        "SETUP.md",
        "LICENSE",
        ".gitignore",
        ".env.example",
    ]
    
    directories = [
        "handlers",
        "keyboards",
        "database",
        "ai",
        "utils",
    ]
    
    print("\nRequired Files:")
    all_required = all(check_file_exists(f, True) for f in required_files)
    
    print("\nRecommended Files:")
    for f in recommended_files:
        check_file_exists(f, False)
    
    print("\nRequired Directories:")
    all_dirs = all(check_file_exists(d, True) for d in directories)
    
    return all_required and all_dirs


def run_basic_tests():
    """Run basic validator tests."""
    print_header("Running Basic Tests")
    
    try:
        from utils.validators import (
            validate_time,
            validate_integer,
            validate_float,
        )
        
        # Test time validation
        assert validate_time("23:30") == "23:30", "Time validation failed"
        print("✅ Time validation works")
        
        # Test integer validation
        is_valid, num = validate_integer("25", 18, 100)
        assert is_valid and num == 25, "Integer validation failed"
        print("✅ Integer validation works")
        
        # Test float validation
        is_valid, num = validate_float("70.5", 30.0, 300.0)
        assert is_valid and num == 70.5, "Float validation failed"
        print("✅ Float validation works")
        
        return True
    except Exception as e:
        print(f"❌ Tests failed: {e}")
        return False


def main():
    """Run all checks."""
    print("\n" + "🔍 AI Life Tracker Bot - Setup Verification" + "\n")
    
    results = {
        "File Structure": check_file_structure(),
        "Environment Variables": check_env_variables(),
        "Dependencies": check_dependencies(),
        "Database Connection": check_database_connection(),
        "AI Service": check_ai_service(),
        "Basic Tests": run_basic_tests(),
    }
    
    # Summary
    print_header("Summary")
    
    all_passed = True
    for check, passed in results.items():
        status = check_mark(passed)
        print(f"{status} {check}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("✅ All checks passed! Your setup is complete.")
        print("\nYou can now run: python bot.py")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("\nRefer to SETUP.md for detailed instructions.")
    
    print("=" * 60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nVerification cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)