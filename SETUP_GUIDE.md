# Quick Setup Guide for Teammates

## For Windows Users 🪟

### TLDR - Super Quick Setup

1. Install Python 3.8+ from [python.org](https://python.org) (**CHECK "Add Python to PATH"**)
2. Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)
3. Open Command Prompt as Administrator
4. Run:
   ```cmd
   cd path\to\portscan_delta_reporter\server
   setup-windows.bat
   ```

### If That Fails

- Read the detailed [Windows Setup Guide](WINDOWS_SETUP.md)
- Try the flexible requirements: `pip install -r requirements-flexible.txt`

---

## For macOS/Linux Users 🍎🐧

### TLDR - Super Quick Setup

```bash
cd server
./setup.sh
```

### If That Fails

```bash
cd server
pip install -r requirements-flexible.txt
```

---

## Common Issues & Quick Fixes

### 1. **"python is not recognized" (Windows)**

- Reinstall Python and check "Add Python to PATH"

### 2. **"Microsoft Visual C++ 14.0 is required" (Windows)**

- Install Visual Studio Build Tools
- Restart Command Prompt

### 3. **pandas/numpy compilation errors**

- Updated requirements.txt now uses compatible versions
- Try: `pip install -r requirements-flexible.txt`

### 4. **SQLAlchemy compatibility errors**

- Fixed in latest requirements.txt
- Uses SQLAlchemy >= 2.0.25

### 5. **Permission errors**

- Run as Administrator (Windows)
- Use `sudo` if needed (macOS/Linux)

---

## What Changed

✅ **Fixed Python 3.13 compatibility issues**

- Updated pandas: `>=2.0.0,<2.3.0`
- Updated SQLAlchemy: `>=2.0.25,<2.1.0`
- Updated numpy: `>=1.24.0,<2.0.0`

✅ **Added Windows support**

- Created `setup-windows.bat`
- Added `WINDOWS_SETUP.md` guide
- Cross-platform requirements

✅ **Made requirements more flexible**

- Version ranges instead of exact pins
- Fallback `requirements-flexible.txt`
- Better error handling in setup scripts

---

## Files Added/Updated

### New Files:

- `server/setup-windows.bat` - Windows setup script
- `WINDOWS_SETUP.md` - Detailed Windows guide
- `server/requirements-flexible.txt` - Fallback requirements
- `SETUP_GUIDE.md` - This file

### Updated Files:

- `server/requirements.txt` - Compatible versions
- `server/setup.sh` - Better error handling
- `README.md` - Cross-platform instructions

---

## Need Help?

1. **Check the error message carefully**
2. **Try the flexible requirements**: `pip install -r requirements-flexible.txt`
3. **Windows users**: Read [WINDOWS_SETUP.md](WINDOWS_SETUP.md)
4. **Still stuck?** Share the exact error message with the team

The setup should now work much better across different systems! 🎉
