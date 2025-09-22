# Windows Setup Guide

This guide helps Windows users set up the Port Scanner Server environment.

## Prerequisites

1. **Python 3.8 or higher** - Download from [python.org](https://python.org)

   - ⚠️ **IMPORTANT**: During installation, check "Add Python to PATH"
   - Verify installation: Open Command Prompt and run `python --version`

2. **Visual C++ Build Tools** (for compiling Python packages)
   - **Option 1**: Install [Visual Studio Community](https://visualstudio.microsoft.com/vs/community/) (free)
   - **Option 2**: Install [Build Tools for Visual Studio](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)
   - **Option 3**: Install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

## Quick Setup

1. Open Command Prompt as Administrator
2. Navigate to the server directory:
   ```cmd
   cd path\to\portscan_delta_reporter\server
   ```
3. Run the Windows setup script:
   ```cmd
   setup-windows.bat
   ```

## Manual Setup (if script fails)

1. **Create virtual environment:**

   ```cmd
   python -m venv venv
   ```

2. **Activate virtual environment:**

   ```cmd
   venv\Scripts\activate.bat
   ```

3. **Upgrade pip:**

   ```cmd
   python -m pip install --upgrade pip
   ```

4. **Install dependencies:**

   ```cmd
   pip install -r requirements.txt
   ```

5. **Initialize database:**
   ```cmd
   python run.py init-db
   ```

## Running the Server

1. **Activate virtual environment:**

   ```cmd
   venv\Scripts\activate.bat
   ```

2. **Start the server:**

   ```cmd
   python run.py
   ```

3. **Access the application:**
   - Open browser to: http://localhost:5000

## Common Windows Issues & Solutions

### Issue: "python is not recognized"

**Solution:**

- Reinstall Python and check "Add Python to PATH"
- Or manually add Python to PATH in Environment Variables

### Issue: "Microsoft Visual C++ 14.0 is required"

**Solution:**

- Install Visual Studio Build Tools (see prerequisites above)
- Restart Command Prompt after installation

### Issue: "Failed building wheel for [package]"

**Solution:**

- Install Visual C++ Build Tools
- Try: `pip install --upgrade setuptools wheel`
- For specific packages, try pre-compiled wheels: `pip install --only-binary=all [package]`

### Issue: Permission denied errors

**Solution:**

- Run Command Prompt as Administrator
- Or use: `pip install --user [package]`

### Issue: Long path names (>260 characters)

**Solution:**

- Enable long path support in Windows 10/11
- Or move project to a shorter path like `C:\projects\portscan\`

## Development Tools (Optional)

For better Windows development experience:

1. **Windows Terminal** (modern terminal)
2. **Git for Windows** (includes Git Bash)
3. **Visual Studio Code** with Python extension
4. **PyCharm Community Edition**

## Troubleshooting

If you encounter issues:

1. **Check Python version:** `python --version`
2. **Check pip version:** `pip --version`
3. **Update pip:** `python -m pip install --upgrade pip`
4. **Clear pip cache:** `pip cache purge`
5. **Reinstall virtual environment:**
   ```cmd
   rmdir /s venv
   python -m venv venv
   ```

## Getting Help

If problems persist:

1. Check the error message carefully
2. Search for the specific error online
3. Consider using WSL (Windows Subsystem for Linux) for a Unix-like environment
4. Ask team members for help with the specific error message
