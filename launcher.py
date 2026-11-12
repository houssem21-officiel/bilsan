# -*- coding: utf-8 -*-
"""Bilsan.exe — يشغّل البرنامج ويفتح نافذته.

- Bilsan.exe              : يشغّل الخادم (إن لم يكن يعمل) ثم يفتح نافذة البرنامج.
- Bilsan.exe --background : يشغّل الخادم فقط (عند تشغيل الحاسوب) حتى تبقى المزامنة تعمل.
"""
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser

PORT = int(os.environ.get("BILSAN_PORT", "5000"))
URL = f"http://localhost:{PORT}/"


def server_up():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def open_window():
    """يفتح البرنامج في نافذة مستقلة (Edge أو Chrome بوضع التطبيق)، وإلا في المتصفح العادي."""
    pf = [os.environ.get(k, "") for k in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")]
    cands = [os.path.join(p, r"Microsoft\Edge\Application\msedge.exe") for p in pf if p] + \
            [os.path.join(p, r"Google\Chrome\Application\chrome.exe") for p in pf if p]
    for exe in cands:
        if os.path.exists(exe):
            try:
                subprocess.Popen([exe, f"--app={URL}", "--start-maximized"], close_fds=True)
                return
            except OSError:
                pass
    webbrowser.open(URL)


def main():
    # لا نبقي مجلد البرنامج «مفتوحًا» (حتى يستطيع التحديث التلقائي استبداله)
    try:
        import paths
        os.chdir(paths.DATA_DIR)
    except OSError:
        pass
    restart = "--restart" in sys.argv  # بعد ربط حاسوب جديد: النافذة مفتوحة أصلًا
    background = "--background" in sys.argv or restart
    if server_up() and not restart:
        if not background:
            open_window()
        return
    if sys.stdout is None or sys.stderr is None:  # نافذة بدون كونسول: السجل في ملف
        import paths
        log = open(paths.data("bilsan.log"), "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = log
    import app  # يجهّز قاعدة البيانات
    t = threading.Thread(target=app.run_server, args=(PORT,), daemon=True)
    t.start()
    if not background:
        for _ in range(120):
            if server_up():
                break
            time.sleep(0.25)
        open_window()
    t.join()


if __name__ == "__main__":
    main()
