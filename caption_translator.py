#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live Caption Translator  v2.0
==============================
Live Captions  ->  Windows UIA (بدون OCR)  ->  Google Translate  ->  Overlay
"""

import os, sys, time, threading, requests
from datetime import datetime
import tkinter as tk
from tkinter import font as tkfont

# ─── تنظیمات ────────────────────────────────────────────────
SCAN_INTERVAL   = 0.12   # ثانیه بین هر خواندن متن
TRANSLATE_EVERY = 0.30   # حداقل فاصله بین دو ترجمه
TRANSLATE_TO    = 'fa'
MIN_TEXT_LEN    = 4
MAX_CACHE       = 150
OVERLAY_ALPHA   = 0.92
OVERLAY_BG      = '#0f172a'
FONT_SIZE       = 18
SHOW_ORIGINAL   = False
# ────────────────────────────────────────────────────────────


# ─── خواندن متن مستقیم از Live Captions (بدون OCR) ─────────

class UIACaptionReader:
    """
    متن را مستقیماً از accessibility tree ویندوز می‌خواند.
    سرعت: ~5-15ms  (در برابر ~300-500ms برای OCR)
    """
    def __init__(self):
        self._ready = False
        self._win   = None
        self._last_search = 0.0
        self._init_uia()

    def _init_uia(self):
        try:
            import uiautomation as auto
            self._auto  = auto
            self._ready = True
        except ImportError:
            self._ready = False

    def _find_win(self):
        now = time.monotonic()
        if now - self._last_search < 2.5 and self._win is not None:
            return self._win
        self._last_search = now
        try:
            w = self._auto.WindowControl(searchDepth=1, Name='Live Captions')
            self._win = w if w.Exists(0.05) else None
        except Exception:
            self._win = None
        return self._win

    # کلمات/پیشوندهایی که نشانه‌ی نام کنترل UI هستند نه متن واقعی
    _JUNK = {'Live Captions', 'DesktopWindowXamlSource', 'LiveCaptions'}
    _JUNK_PREFIX = ('Windows.', 'Microsoft.', 'Desktop', 'XAML', 'Xaml')

    def _is_junk(self, s: str) -> bool:
        if s in self._JUNK:
            return True
        if any(s.startswith(p) for p in self._JUNK_PREFIX):
            return True
        # نام‌های کلاسی: یک کلمه بلند بدون فاصله که با حرف بزرگ شروع می‌شه
        if len(s) > 12 and ' ' not in s and s[0].isupper():
            return True
        return False

    # فقط این نوع کنترل‌ها متن واقعی دارند
    _TEXT_TYPES = {'TextControl', 'DocumentControl', 'EditControl'}
    # این کنترل‌ها دکمه/منو هستند — متنشان کپشن نیست
    _SKIP_TYPES = {'ButtonControl', 'MenuItemControl', 'TabItemControl',
                   'ToolBarControl', 'StatusBarControl', 'TitleBarControl'}

    def _gather(self, ctrl, out, depth=0):
        if depth > 8:
            return
        try:
            ctype = ctrl.ControlTypeName
            # کنترل‌های دکمه‌ای را کلاً رد کن (و فرزندانشان را هم)
            if ctype in self._SKIP_TYPES:
                return
            name = ctrl.Name
            if name:
                name = name.strip()
                # فقط از TextControl/Document بخوان، نه همه کنترل‌ها
                if (ctype in self._TEXT_TYPES
                        and len(name) >= MIN_TEXT_LEN
                        and not self._is_junk(name)):
                    out.append(name)
        except Exception:
            pass
        try:
            for child in ctrl.GetChildren():
                self._gather(child, out, depth + 1)
        except Exception:
            pass

    def read(self):
        """→ (text | None, error | None)"""
        if not self._ready:
            return None, "uiautomation نصب نیست — install.bat را اجرا کنید"

        win = self._find_win()
        if not win:
            return None, "Live Captions باز نیست  (Win + Ctrl + L)"

        try:
            parts = []
            self._gather(win, parts)
            seen = dict.fromkeys(parts)   # dedup با حفظ ترتیب
            result = ' '.join(seen.keys())
            return (result if result else None), None
        except Exception as exc:
            self._win = None
            return None, str(exc)


# ─── ترجمه سریع ────────────────────────────────────────────

class TranslationService:
    API = 'https://translate.googleapis.com/translate_a/single'

    def __init__(self, to_lang='fa'):
        self._to   = to_lang
        self._sess = requests.Session()
        self._sess.headers['User-Agent'] = 'Mozilla/5.0'
        self._cache: dict[str, str] = {}
        self._order: list[str]      = []

    def translate(self, text: str) -> str:
        if not text or len(text) < MIN_TEXT_LEN:
            return ''
        if text in self._cache:
            return self._cache[text]
        try:
            r = self._sess.get(self.API, params={
                'client': 'gtx', 'sl': 'auto',
                'tl': self._to, 'dt': 't', 'q': text
            }, timeout=5)
            result = ''.join(p[0] for p in r.json()[0] if p[0])
            self._cache[text] = result
            self._order.append(text)
            if len(self._order) > MAX_CACHE:
                del self._cache[self._order.pop(0)]
            return result
        except Exception as exc:
            return f'⚠  {exc}'


# ─── Overlay ────────────────────────────────────────────────

class OverlayWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('ترجمه زنده')
        self.root.wm_attributes('-topmost', True)
        self.root.wm_attributes('-alpha', OVERLAY_ALPHA)
        self.root.configure(bg=OVERLAY_BG)
        self.root.resizable(True, True)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f'760x220+{(sw-760)//2}+{sh-280}')
        self.root.minsize(300, 100)
        self._last = None
        self._build()

    def _build(self):
        # نوار وضعیت کوچک زیر title bar
        status = tk.Frame(self.root, bg='#1e293b', pady=2)
        status.pack(fill='x')
        self._dot = tk.Label(status, bg='#1e293b', fg='#ef4444',
                              text='⬤', font=('Segoe UI', 8))
        self._dot.pack(side='right', padx=6)
        tk.Label(status, bg='#1e293b', fg='#475569',
                 text='ترجمه زنده', font=('Segoe UI', 8)).pack(side='left', padx=6)

        fa_font = next((f for f in ('Vazirmatn','Vazir','B Nazanin','Tahoma')
                        if f in tkfont.families()), 'Tahoma')

        # Text + Scrollbar
        frame = tk.Frame(self.root, bg=OVERLAY_BG)
        frame.pack(fill='both', expand=True, padx=6, pady=6)

        sb = tk.Scrollbar(frame, orient='vertical', bg='#1e293b',
                          troughcolor='#0f172a', width=10)
        sb.pack(side='right', fill='y')

        self._fa = tk.Text(
            frame, bg=OVERLAY_BG, fg='#f1f5f9',
            font=(fa_font, FONT_SIZE),
            wrap='word', relief='flat', bd=0,
            state='disabled', cursor='arrow',
            yscrollcommand=sb.set,
            padx=8, pady=6,
        )
        self._fa.tag_configure('rtl', justify='right')
        self._fa.pack(side='left', fill='both', expand=True)
        sb.config(command=self._fa.yview)

        self.root.bind('<Control-q>', lambda _: self.root.destroy())

    def update(self, persian: str, original: str = '', ok: bool = True):
        self.root.after(0, self._apply, persian, original, ok)

    def _apply(self, persian, original, ok):
        if persian == self._last:
            return
        self._last = persian
        self._fa.config(state='normal')
        self._fa.delete('1.0', 'end')
        self._fa.insert('end', persian or '...', 'rtl')
        self._fa.config(state='disabled')
        self._fa.see('end')
        self._dot.config(fg='#22c55e' if ok else '#ef4444')

    def run(self):
        self.root.mainloop()


# ─── ذخیره ترنسکریپت ────────────────────────────────────────

class TranscriptLogger:
    """
    هر بار که Live Captions باز می‌شود یک فایل جدید در پوشه data می‌سازد.
    فقط خطوط کامل‌شده را ذخیره می‌کند — نه هر تغییر کلمه‌ای.
    منطق: خط آخر هنوز در حال تایپ است؛ وقتی خط جدیدی آمد،
    خط قبلی کامل شده و ذخیره می‌شود.
    """
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

    # پیام‌های سیستمی که نباید ذخیره شوند
    SKIP_PREFIXES = ('Ready to show live captions', 'Live Captions is')

    def __init__(self):
        os.makedirs(self.DATA_DIR, exist_ok=True)
        self._file         = None
        self._path         = None
        self._open_time    = None
        self._logged       = set()   # خطوطی که قبلاً ذخیره شدند
        self._pending_last = ''      # آخرین خط که هنوز ممکن است ادامه داشته باشد

    def _is_system_msg(self, line: str) -> bool:
        return any(line.startswith(p) for p in self.SKIP_PREFIXES)

    def on_open(self):
        if self._file:
            return
        self._open_time    = datetime.now()
        self._logged       = set()
        self._pending_last = ''
        fname = self._open_time.strftime('%Y-%m-%d_%H-%M-%S') + '.txt'
        self._path = os.path.join(self.DATA_DIR, fname)
        self._file = open(self._path, 'w', encoding='utf-8')
        self._file.write(f'Live Captions  {self._open_time.strftime("%Y/%m/%d  %H:%M:%S")}\n')
        self._file.write('=' * 60 + '\n\n')
        self._file.flush()
        print(f'[LOG] {self._path}')

    def on_close(self):
        if not self._file:
            return
        # آخرین خط pending را هم ذخیره کن
        self._save_line(self._pending_last)
        self._file.write(f'\n--- end  {datetime.now().strftime("%H:%M:%S")} ---\n')
        self._file.close()
        self._file         = None
        self._logged       = set()
        self._pending_last = ''
        print(f'[LOG] saved: {self._path}')

    def _save_line(self, line: str):
        """یک خط را ذخیره کن (اگر جدید و معتبر باشد)"""
        line = line.strip()
        if not line or line in self._logged or self._is_system_msg(line):
            return
        self._logged.add(line)
        ts = datetime.now().strftime('%H:%M:%S')
        self._file.write(f'[{ts}]  {line}\n')
        self._file.flush()

    def append(self, text: str):
        """
        متن فعلی Live Captions را پردازش کن.
        همه خطوط به‌جز آخری کامل‌اند — آن‌ها را ذخیره کن.
        خط آخر هنوز در حال رشد است — منتظر بمان.
        """
        if not self._file:
            return

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            return

        # همه خطوط به‌جز آخری را ذخیره کن
        for line in lines[:-1]:
            self._save_line(line)

        # خط آخر را به عنوان pending نگه دار
        self._pending_last = lines[-1]


# ─── برنامه اصلی ────────────────────────────────────────────

class App:
    def __init__(self):
        self.reader     = UIACaptionReader()
        self.translator = TranslationService(TRANSLATE_TO)
        self.ui         = OverlayWindow()
        self.logger     = TranscriptLogger()

        self._running          = True
        self._last_raw         = ''
        self._last_translated  = ''
        self._last_trans_t     = 0.0
        self._translating      = False
        self._captions_open    = False   # آیا Live Captions الان باز است؟

        threading.Thread(target=self._loop, daemon=True).start()

    def _do_translate(self, text):
        try:
            fa = self.translator.translate(text)
            if fa:
                self._last_translated = text
                self.ui.update(fa, original=text, ok=True)
        except Exception as exc:
            self.ui.update(f'⚠  {exc}', ok=False)
        finally:
            self._translating = False

    def _translate_async(self, text):
        if self._translating:
            return
        self._translating  = True
        self._last_trans_t = time.monotonic()
        threading.Thread(target=self._do_translate, args=(text,), daemon=True).start()

    def _loop(self):
        import uiautomation as auto
        with auto.UIAutomationInitializerInThread():
            while self._running:
                try:
                    raw, err = self.reader.read()

                    if err:
                        # Live Captions بسته است
                        if self._captions_open:
                            self._captions_open = False
                            self.logger.on_close()
                        self.ui.update(err, ok=False)
                    else:
                        # Live Captions باز است
                        if not self._captions_open:
                            self._captions_open = True
                            self.logger.on_open()

                        if raw:
                            # ذخیره ترنسکریپت
                            self.logger.append(raw)
                            # ترجمه
                            if raw != self._last_translated:
                                self._last_raw = raw
                                now = time.monotonic()
                                if now - self._last_trans_t >= TRANSLATE_EVERY:
                                    self._translate_async(raw)

                except Exception as exc:
                    self.ui.update(f'⚠  {exc}', ok=False)
                time.sleep(SCAN_INTERVAL)

    def run(self):
        try:
            self.ui.run()
        finally:
            self._running = False
            self.logger.on_close()


# ─── نقطه ورود ──────────────────────────────────────────────

def main():
    print('Live Caption Translator v2.0')
    print('----------------------------')

    try:
        import uiautomation
        print('[OK] uiautomation ready')
    except ImportError:
        print('[ERROR] uiautomation not installed!')
        print('  Run:  pip install uiautomation')
        input('Press Enter to exit...')
        sys.exit(1)

    print()
    print('  Win + Ctrl + L  ->  Open Live Captions')
    print('  Right-click overlay  ->  Close')
    print('  Ctrl+Q  ->  Exit')
    print()

    App().run()


if __name__ == '__main__':
    main()