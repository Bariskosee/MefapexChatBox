# 🐍 Python Version Compatibility Guide

This guide helps you set up MEFAPEX ChatBox with different Python versions.

## 🎯 Supported Python Versions

| Python Version | Support Level | Notes |
|----------------|---------------|-------|
| 3.11.x | ✅ **Recommended** | Fully tested, all packages work perfectly |
| 3.12.x | ✅ **Excellent** | Fully supported, all features working |
| 3.13.x | ⚠️ **Compatible** | Works with special handling, some packages need newer versions |

## 🚀 Quick Setup by Python Version

### Python 3.11 & 3.12 (Recommended)

```bash
# Clone repository
git clone https://github.com/Bariskosee/MefapexChatBox.git
cd MefapexChatBox

# Check compatibility
python check_compatibility.py

# Auto setup (handles everything)
python setup.py

# Start application
./run.sh  # or ./run.bat on Windows
```

### Python 3.13 (Special Instructions)

```bash
# Clone repository
git clone https://github.com/Bariskosee/MefapexChatBox.git
cd MefapexChatBox

# Check compatibility first
python check_compatibility.py

# Option 1: Use auto setup (recommended)
python setup.py

# Option 2: Manual setup with Python 3.13 requirements
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-python313.txt

# Start application
python main.py
```

## 🔧 Troubleshooting by Python Version

### Python 3.13 Common Issues

**Issue: `greenlet` compilation error**
```bash
# Solution: Install precompiled version
pip install greenlet>=3.2.0
```

**Issue: `scikit-learn` compatibility error**
```bash
# Solution: Use newer version
pip install scikit-learn>=1.3.0
```

**Issue: Virtual environment Python version mismatch**
```bash
# Solution: Recreate virtual environment
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-python313.txt
```

### General Issues

**Issue: `No module named 'qdrant_client'`**
```bash
# Check which Python you're using
which python
python --version

# Ensure you're in the right virtual environment
source .venv/bin/activate
pip install qdrant-client
```

**Issue: Different Python versions in terminal vs virtual env**
```bash
# Check current setup
python --version                    # System Python
source .venv/bin/activate
python --version                    # Virtual env Python

# If different, recreate virtual environment
deactivate
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 🧪 Testing Your Setup

After installation, verify everything works:

```bash
# Check Python compatibility
python check_compatibility.py

# Test critical imports
python -c "import fastapi, qdrant_client, transformers; print('✅ All imports successful!')"

# Start application
python main.py
```

## 📋 Version-Specific Requirements Files

- `requirements.txt` - Main requirements (works with 3.11, 3.12, some 3.13)
- `requirements-python313.txt` - Optimized for Python 3.13

## 🆘 Getting Help

If you encounter issues:

1. **Run compatibility checker**: `python check_compatibility.py`
2. **Check Python version**: `python --version`
3. **Verify virtual environment**: `source .venv/bin/activate && python --version`
4. **Try Python 3.13 requirements**: `pip install -r requirements-python313.txt`
5. **Open an issue**: [GitHub Issues](https://github.com/Bariskosee/MefapexChatBox/issues)

## 🔄 Migration Between Python Versions

If you need to switch Python versions:

```bash
# 1. Remove existing virtual environment
rm -rf .venv

# 2. Create new virtual environment with desired Python
python3.11 -m venv .venv  # For Python 3.11
# OR
python3.12 -m venv .venv  # For Python 3.12
# OR  
python3.13 -m venv .venv  # For Python 3.13

# 3. Activate and install
source .venv/bin/activate

# 4. Install appropriate requirements
pip install -r requirements.txt              # For 3.11/3.12
# OR
pip install -r requirements-python313.txt    # For 3.13

# 5. Test setup
python check_compatibility.py
python main.py
```

## ✨ Pro Tips

- **Use Python 3.11 or 3.12** for the smoothest experience
- **Always check compatibility** before starting setup
- **Use virtual environments** to avoid conflicts
- **Keep requirements files updated** for your Python version
- **Test after installation** to ensure everything works
