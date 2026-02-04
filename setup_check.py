"""
Setup validation script to verify environment configuration.
"""

import sys
from pathlib import Path
import os

def check_python_version():
    """Check Python version >= 3.9"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9+ required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_env_file():
    """Check if .env file exists"""
    env_path = Path('.env')
    if not env_path.exists():
        print("❌ .env file not found")
        print("   Create one using: copy .env.example .env")
        return False
    print("✅ .env file exists")
    return True

def check_env_variables():
    """Check required environment variables"""
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API key for embeddings and agent',
        'SUPABASE_URL': 'Supabase project URL',
        'SUPABASE_SERVICE_KEY': 'Supabase service role key'
    }
    
    all_set = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value or value.startswith('your_'):
            print(f"❌ {var} not configured ({description})")
            all_set = False
        else:
            masked = value[:10] + '...' if len(value) > 10 else '***'
            print(f"✅ {var} = {masked}")
    
    return all_set

def check_directories():
    """Check if required directories exist"""
    dirs = ['data', 'checkpoints', 'logs']
    all_exist = True
    
    for dir_name in dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"✅ {dir_name}/ directory exists")
        else:
            print(f"⚠️  {dir_name}/ will be created automatically")
    
    return True

def check_dependencies():
    """Check if critical dependencies are installed"""
    packages = [
        'crawl4ai',
        'supabase',
        'openai',
        'pydantic',
        'rich'
    ]
    
    all_installed = True
    for package in packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} installed")
        except ImportError:
            print(f"❌ {package} not installed")
            all_installed = False
    
    if not all_installed:
        print("\n   Install with: pip install -r requirements.txt")
    
    return all_installed

def main():
    """Run all validation checks"""
    print("\n" + "="*70)
    print("CCR COMPLIANCE AGENT - SETUP VALIDATION")
    print("="*70 + "\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Environment File", check_env_file),
        ("Environment Variables", check_env_variables),
        ("Dependencies", check_dependencies),
        ("Directories", check_directories)
    ]
    
    results = {}
    
    for name, check_func in checks:
        print(f"\n{'─'*70}")
        print(f"Checking: {name}")
        print(f"{'─'*70}")
        results[name] = check_func()
    
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70 + "\n")
    
    all_passed = all(results.values())
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("\n" + "="*70 + "\n")
    
    if all_passed:
        print("🎉 All checks passed! You're ready to start.\n")
        print("Next steps:")
        print("  1. Set up Supabase schema (see README.md)")
        print("  2. Run: python crawler/url_discoverer.py")
        print("  3. Run: python crawler/section_extractor.py")
        print("  4. Run: python coverage_tracker.py")
        print("  5. Run: python index_pipeline.py")
        print("  6. Run: python cli.py\n")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix the issues above.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
