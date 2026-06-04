# Live Caption Translator

Real-time translation of Windows 11 Live Captions into Persian (Farsi), displayed as an always-on-top overlay.

## How it works

1. Windows 11 Live Captions listens to system audio and displays captions on screen
2. This app reads the caption text directly from Windows Accessibility API (no OCR)
3. Text is translated to Persian via Google Translate
4. Translation is shown in a resizable overlay window on top of everything

## Requirements

- Windows 11 (Live Captions is a Windows 11 feature)
- Python 3.10+

## Installation

Run as Administrator:

```
install.bat
```

This installs all Python dependencies and Tesseract OCR automatically.

## Usage

1. Open Live Captions: `Win + Ctrl + L`
2. Run the translator:

```
run.bat
```

Or directly:

```
python caption_translator.py
```

## Transcript saving

Every session is automatically saved to the `data/` folder as a `.txt` file named with the date and time Live Captions was opened:

```
data/
  2026-06-04_14-35-22.txt
  2026-06-04_18-10-05.txt
```

## Settings

Edit the top of `caption_translator.py` to customize:

| Setting | Default | Description |
|---|---|---|
| `TRANSLATE_TO` | `'fa'` | Target language (fa = Persian) |
| `SCAN_INTERVAL` | `0.12` | Seconds between reads |
| `TRANSLATE_EVERY` | `0.30` | Minimum seconds between translations |
| `FONT_SIZE` | `18` | Overlay font size |
| `OVERLAY_ALPHA` | `0.92` | Overlay transparency (0–1) |
| `SHOW_ORIGINAL` | `False` | Show original caption text above translation |

## Dependencies

- [uiautomation](https://github.com/yinkaisheng/Python-UIAutomation-for-Windows) — reads Live Captions text via Windows Accessibility API
- [requests](https://requests.readthedocs.io/) — calls Google Translate API
- [pywin32](https://github.com/mhammond/pywin32) — Windows API access
