# auto-reg

GUI tool for creating mail.tm accounts and reading inbox via API/IMAP.

## Requirements
- Python 3.10+
- Windows (for best UI + sound support)

Install deps:
```
pip install -r requirements.txt
```

## Run
```
python main.py
```

## C++ version (console)
- Source: `cpp/auto_reg_cpp.cpp`
- Build on Windows:
```
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_cpp.ps1
```
- Binary output: `build/auto_reg_cpp.exe`

## Notes
- Local data files `accounts.txt` and `accounts.xlsx` are ignored by git.
- Sound notification plays when new emails arrive.
