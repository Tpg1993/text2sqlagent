# Test Files

This directory contains debugging and test scripts used during development.

## Files

- **debug_new_sdk.py** - Script to test the Google GenAI SDK and list available models
- **check_db.py** - Database schema inspection tool
- **final_e2e_test.py** - End-to-end API test script

## Usage

These scripts were used to:
1. Debug API connectivity issues
2. Verify database initialization
3. Test the complete application flow

You can run any of these from the backend directory:
```bash
python tests/check_db.py
python tests/final_e2e_test.py
```
