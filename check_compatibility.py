#!/usr/bin/env python3
"""
MEFAPEX ChatBox - Python Environment Compatibility Checker
Helps users verify their Python setup before installation
"""

import sys
import subprocess
import platform
from pathlib import Path

def print_header():
    """Print checker header"""
    print("🔍 MEFAPEX ChatBox - Python Compatibility Checker")
    print("=" * 55)

def check_python_version():
    """Check Python version compatibility"""
    print("\n🐍 Python Version Check:")
    
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    print(f"   Current Python: {version_str}")
    print(f"   Python Path: {sys.executable}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("❌ INCOMPATIBLE: Python 3.11+ required!")
        print("   Download Python 3.11+: https://www.python.org/downloads/")
        return False
    elif version.major == 3 and version.minor == 11:
        print("✅ PERFECT: Python 3.11 (fully supported)")
        return True
    elif version.major == 3 and version.minor == 12:
        print("✅ EXCELLENT: Python 3.12 (fully supported)")
        return True
    elif version.major == 3 and version.minor == 13:
        print("⚠️  COMPATIBLE: Python 3.13 (may need special handling)")
        print("   Note: Some packages may require newer versions")
        return True
    else:
        print("⚠️  UNKNOWN: Python version not tested")
        print("   May work but use at your own risk")
        return True

def check_system_info():
    """Check system information"""
    print("\n🖥️  System Information:")
    print(f"   OS: {platform.system()} {platform.release()}")
    print(f"   Architecture: {platform.machine()}")
    print(f"   Platform: {platform.platform()}")

def check_virtual_env():
    """Check virtual environment status"""
    print("\n📦 Virtual Environment Check:")
    
    venv_path = Path(".venv")
    if venv_path.exists():
        print("✅ Virtual environment found: .venv/")
        
        # Check pyvenv.cfg for version info
        pyvenv_cfg = venv_path / "pyvenv.cfg"
        if pyvenv_cfg.exists():
            try:
                with open(pyvenv_cfg, 'r') as f:
                    content = f.read()
                    for line in content.split('\n'):
                        if line.startswith('version'):
                            venv_version = line.split('=')[1].strip()
                            current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
                            
                            if venv_version.startswith(current_version):
                                print(f"✅ Virtual env Python version: {venv_version} (compatible)")
                                return True
                            else:
                                print(f"⚠️  Virtual env Python version: {venv_version}")
                                print(f"   Current Python: {current_version}")
                                print("   Recommendation: Recreate virtual environment")
                                return False
            except Exception as e:
                print(f"⚠️  Could not read pyvenv.cfg: {e}")
                return False
    else:
        print("📝 No virtual environment found")
        print("   Will be created during setup")
        return True

def check_pip():
    """Check pip availability"""
    print("\n📦 Package Manager Check:")
    
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ pip is available")
            pip_version = result.stdout.strip()
            print(f"   {pip_version}")
            return True
        else:
            print("❌ pip is not available")
            return False
    except Exception as e:
        print(f"❌ pip check failed: {e}")
        return False

def check_critical_tools():
    """Check for critical system tools"""
    print("\n🛠️  System Tools Check:")
    
    tools = ["git", "curl"]
    all_good = True
    
    for tool in tools:
        try:
            result = subprocess.run([tool, "--version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {tool} is available")
            else:
                print(f"⚠️  {tool} not found (optional)")
        except FileNotFoundError:
            print(f"⚠️  {tool} not found (optional)")
        except Exception:
            print(f"⚠️  {tool} check failed (optional)")
    
    return all_good

def provide_recommendations(python_ok, venv_ok, pip_ok):
    """Provide setup recommendations"""
    print("\n💡 Recommendations:")
    
    if not python_ok:
        print("🔴 CRITICAL: Update Python to 3.11+")
        print("   1. Download from: https://www.python.org/downloads/")
        print("   2. Install and restart terminal")
        print("   3. Run this checker again")
        return
    
    if not pip_ok:
        print("🔴 CRITICAL: Install pip")
        print("   python -m ensurepip --upgrade")
        return
    
    if not venv_ok:
        print("🟡 RECOMMENDED: Recreate virtual environment")
        print("   rm -rf .venv")
        print("   python -m venv .venv")
    
    print("🟢 READY: Run setup script")
    print("   python setup.py")

def main():
    """Main checker function"""
    print_header()
    
    python_ok = check_python_version()
    check_system_info()
    venv_ok = check_virtual_env()
    pip_ok = check_pip()
    check_critical_tools()
    
    provide_recommendations(python_ok, venv_ok, pip_ok)
    
    print("\n" + "=" * 55)
    if python_ok and pip_ok:
        print("🎉 Your system is ready for MEFAPEX ChatBox!")
    else:
        print("⚠️  Please address the issues above before proceeding")
    print("=" * 55)

if __name__ == "__main__":
    main()
