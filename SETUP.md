# Development Setup

## Quick Start with Virtual Environment

This project uses Python 3.12 with a virtual environment for local development.

### 1. Create Virtual Environment

```bash
python3.12 -m venv venv
```

### 2. Activate Virtual Environment

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install CLI in Development Mode

```bash
pip install -e .
```

### 5. Verify Installation

```bash
cmcli --version
# Should output: cmcli, version 0.1.0

cmcli --help
# Should show available commands
```

### 6. Run Tests

```bash
pytest tests/ -v
```

### 7. Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your HubSpot credentials:

```
HUBSPOT_ACCESS_TOKEN=pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
HUBSPOT_ACCOUNT_ID=12345678
```

### 8. Test the CLI

```bash
# Verify HubSpot access
cmcli hubspot verify

# Update timestamps in dataset
cmcli update

# Seed HubSpot (when ready)
cmcli hubspot seed
```

## Deactivating Virtual Environment

When you're done working:

```bash
deactivate
```

## Troubleshooting

### Python Version

Ensure you have Python 3.12 installed:

```bash
python3.12 --version
```

If not installed, download from [python.org](https://www.python.org/downloads/) or use a package manager:

**macOS (Homebrew):**
```bash
brew install python@3.12
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv
```

### Virtual Environment Issues

If you encounter issues with the virtual environment:

1. Delete the venv directory:
   ```bash
   rm -rf venv
   ```

2. Recreate it:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install -e .
   ```

### Import Errors

If you see import errors after installation, ensure:

1. Virtual environment is activated (you should see `(venv)` in your prompt)
2. Package is installed in development mode: `pip install -e .`
3. You're in the project root directory

## Development Workflow

1. **Activate venv**: `source venv/bin/activate`
2. **Make changes** to code
3. **Run tests**: `pytest tests/ -v`
4. **Test CLI**: `cmcli <command>`
5. **Deactivate**: `deactivate` when done

## IDE Setup

### VS Code

Recommended extensions:
- Python (Microsoft)
- Pylance (Microsoft)

Select the virtual environment interpreter:
1. Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
2. Type "Python: Select Interpreter"
3. Choose `./venv/bin/python`

### PyCharm

1. Go to Settings → Project → Python Interpreter
2. Click gear icon → Add
3. Select "Existing environment"
4. Choose `./venv/bin/python`

## Running with Verbose Output

For debugging:

```bash
cmcli --verbose hubspot verify
cmcli --verbose hubspot seed
```

## Code Quality

Run tests with coverage:

```bash
pytest tests/ --cov=cmcli --cov-report=html
open htmlcov/index.html  # View coverage report