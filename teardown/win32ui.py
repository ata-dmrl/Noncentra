"""Minimal Win32 UI automation over ctypes (no third-party deps).

Classic Win32/MFC controls answer WM_GETTEXT / WM_SETTEXT / BM_CLICK / CB_* messages,
which is all the G*Power harvest needs.
"""
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)

WM_GETTEXT, WM_GETTEXTLENGTH, WM_SETTEXT = 0x000D, 0x000E, 0x000C
WM_COMMAND, WM_KILLFOCUS, WM_SETFOCUS = 0x0111, 0x0008, 0x0007
BM_CLICK = 0x00F5
CB_GETCOUNT, CB_GETCURSEL, CB_SETCURSEL, CB_GETLBTEXT, CB_GETLBTEXTLEN = 0x0146, 0x0147, 0x014E, 0x0148, 0x0149
CBN_SELCHANGE, EN_CHANGE, EN_KILLFOCUS = 1, 0x0300, 0x0200
SMTO_ABORTIFHUNG = 0x0002

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
                                       wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
user32.GetParent.restype = wintypes.HWND
user32.GetDlgCtrlID.argtypes = [wintypes.HWND]


def send(hwnd, msg, wparam=0, lparam=0, timeout_ms=10_000):
    result = ctypes.c_size_t()
    ok = user32.SendMessageTimeoutW(hwnd, msg, wparam, lparam, SMTO_ABORTIFHUNG, timeout_ms,
                                    ctypes.byref(result))
    if not ok:
        raise TimeoutError(f"window {hwnd:#x} did not answer message {msg:#x}")
    return result.value


def class_name(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def get_text(hwnd):
    n = send(hwnd, WM_GETTEXTLENGTH)
    buf = ctypes.create_unicode_buffer(n + 1)
    send(hwnd, WM_GETTEXT, n + 1, ctypes.addressof(buf))
    return buf.value


def set_text(hwnd, text):
    buf = ctypes.create_unicode_buffer(text)
    send(hwnd, WM_SETTEXT, 0, ctypes.addressof(buf))
    _notify_parent(hwnd, EN_CHANGE)
    _notify_parent(hwnd, EN_KILLFOCUS)


def _notify_parent(hwnd, code):
    parent = user32.GetParent(hwnd)
    cid = user32.GetDlgCtrlID(hwnd)
    send(parent, WM_COMMAND, (code << 16) | (cid & 0xFFFF), hwnd)


def click(hwnd):
    send(hwnd, BM_CLICK)


def combo_items(hwnd):
    items = []
    for i in range(send(hwnd, CB_GETCOUNT)):
        n = send(hwnd, CB_GETLBTEXTLEN, i)
        buf = ctypes.create_unicode_buffer(n + 1)
        send(hwnd, CB_GETLBTEXT, i, ctypes.addressof(buf))
        items.append(buf.value)
    return items


def combo_select(hwnd, text):
    items = combo_items(hwnd)
    matches = [i for i, s in enumerate(items) if s.strip() == text or s.strip().startswith(text)]
    if not matches:
        raise ValueError(f"{text!r} not in combo: {items}")
    send(hwnd, CB_SETCURSEL, matches[0])
    _notify_parent(hwnd, CBN_SELCHANGE)
    return items[matches[0]]


def children(parent):
    """All descendant windows as dicts, in Z order."""
    out = []

    @WNDENUMPROC
    def cb(h, _):
        out.append(h)
        return True

    user32.EnumChildWindows(parent, cb, 0)
    rows = []
    for h in out:
        try:
            text = get_text(h)
        except TimeoutError:
            text = None
        rect = wintypes.RECT()
        user32.GetWindowRect(h, ctypes.byref(rect))
        rows.append({"hwnd": h, "parent": user32.GetParent(h) or 0, "id": user32.GetDlgCtrlID(h),
                     "cls": class_name(h), "text": text, "visible": bool(user32.IsWindowVisible(h)),
                     "rect": (rect.left, rect.top, rect.right, rect.bottom)})
    return rows


def top_windows(pid):
    """Visible top-level windows of process `pid`."""
    found = []

    @WNDENUMPROC
    def cb(h, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(h):
            found.append(h)
        return True

    user32.EnumWindows(cb, 0)
    return found


def main_window(pid):
    """The MFC frame window of `pid` (dialog boxes have class #32770 and are skipped)."""
    for h in top_windows(pid):
        if class_name(h).startswith("Afx:") and get_text(h):
            return h
    raise LookupError(f"no main window for pid {pid}")


def dismiss_dialogs(pid):
    """Close every modal #32770 box of `pid` with its first button; return their texts."""
    texts = []
    for h in top_windows(pid):
        if class_name(h) != "#32770":
            continue
        kids = children(h)
        texts.append(" ".join(c["text"] for c in kids if c["cls"] == "Static" and c["text"]))
        buttons = [c["hwnd"] for c in kids if c["cls"] == "Button"]
        if buttons:
            user32.PostMessageW(buttons[0], BM_CLICK, 0, 0)
    if texts:
        time.sleep(0.3)
    return texts


def wait(seconds):
    time.sleep(seconds)
