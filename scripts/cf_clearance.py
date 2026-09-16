"""
Bot-wall clearance cookies: Cloudflare's JS "Just a moment..." managed
challenge (marinetraffic.org, marinevesseltraffic.com, ...), AWS WAF
(investors.seatrium.com — answers curl with an empty HTTP 202 and only serves
the page to a browser holding its `aws-waf-token`) and Imperva/Incapsula.

Why this exists (2026-09-16): the challenge cannot be passed by curl, by
TLS-fingerprint impersonation, or by any browser Playwright launches (headless
or headed, Chromium/Chrome/Firefox — Turnstile spots the automation flags).
It IS passed, in about five seconds, by a real Google Chrome that we launch
ourselves with a scratch profile and drive over the DevTools protocol using
only the Target/DOM/Storage domains (never `Runtime.enable`, the tell that
Turnstile looks for). The `cf_clearance` cookie Chrome receives is valid for a
year and is honoured for plain `curl` requests as long as the User-Agent
string matches the Chrome that earned it (it is also bound to our egress IP,
so it silently stops working when the laptop changes networks — refresh again).

Library usage (fetch.py calls these; nothing else should need to):
    from cf_clearance import cookie_for, refresh, ClearanceError

    hit = cookie_for("https://www.marinetraffic.org/...")   # (cookie header, ua) | None
    refresh([url])          # opens Chrome, waits for the challenge, stores the cookies

CLI:
    python scripts/cf_clearance.py https://www.marinetraffic.org/ https://www.marinevesseltraffic.com/
    python scripts/cf_clearance.py --show

Store: work/cf_clearance.json (gitignored — the cookie is a credential-like
token for this IP; never commit it). Set LNGCT_NO_BROWSER=1 to forbid the
Chrome launch (CI, unattended runs): fetch.py then reports the wall as blocked.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from paths import work_dir

CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
)
CDP_PORT = int(os.environ.get("LNGCT_CDP_PORT", "9333"))
CHALLENGE_TITLES = ("just a moment", "verify you are human", "attention required",
                    "checking your browser", "please wait", "are you a robot",
                    "access denied", "human verification")
# A challenge page can have an empty title (AWS WAF, Imperva) — Chrome then
# reports the URL as the title — so the rendered DOM is checked as well.
CHALLENGE_BODY_MARKERS = ("challenge-platform", "cf-chl", "cf_chl_",           # Cloudflare
                          "awswaf", "challenge-container",                    # AWS WAF
                          "_incapsula_resource", "incapsula incident",        # Imperva
                          "px-captcha")                                       # PerimeterX
# Cookie families that carry a bot-wall clearance. Everything else the browser
# holds (analytics, consent) stays out of the store.
WALL_COOKIE_PREFIXES = ("cf_clearance",                      # Cloudflare
                        "aws-waf-token",                     # AWS WAF
                        "incap_ses_", "visid_incap_", "nlbi_", "reese84",   # Imperva
                        "_px", "px")                          # PerimeterX


class ClearanceError(RuntimeError):
    pass


def store_path() -> Path:
    return work_dir() / "cf_clearance.json"


def profile_dir() -> Path:
    return work_dir() / "chrome_profile"


def browser_allowed() -> bool:
    return os.environ.get("LNGCT_NO_BROWSER", "") not in ("1", "true", "yes")


def is_wall_cookie(name: str) -> bool:
    return any(name.startswith(p) for p in WALL_COOKIE_PREFIXES)


def load_store() -> dict:
    """{"ua": str, "cookies": {domain: {"cookies": {name: value}, "expires": float, "saved": float}}}

    Entries written before 2026-09-16 (evening) hold a single "value" (the
    cf_clearance cookie) instead of "cookies"; both shapes are read.
    """
    try:
        d = json.loads(store_path().read_text())
        d.setdefault("cookies", {})
        return d
    except (OSError, ValueError):
        return {"ua": "", "cookies": {}}


def save_store(store: dict) -> None:
    p = store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(store, indent=1))


def _domain_matches(host: str, domain: str) -> bool:
    d = domain.lstrip(".").lower()
    return host == d or host.endswith("." + d)


def _entry_cookies(entry: dict) -> dict[str, str]:
    if entry.get("cookies"):
        return {k: v for k, v in entry["cookies"].items() if v}
    if entry.get("value"):                       # pre-generalisation shape
        return {"cf_clearance": entry["value"]}
    return {}


def cookie_for(url: str, store: dict | None = None) -> tuple[str, str] | None:
    """
    (Cookie header value, User-Agent it was earned with) for url's host, or
    None. Cookies from every matching domain (host, then each parent) are
    joined, so an Imperva site whose cookies sit on both `www.x.com` and
    `.x.com` replays as one header.
    """
    host = (urlsplit(url).hostname or "").lower()
    if not host:
        return None
    store = store if store is not None else load_store()
    now = time.time()
    jar: dict[str, str] = {}
    for domain, c in store.get("cookies", {}).items():
        if _domain_matches(host, domain) and c.get("expires", 0) > now:
            jar.update(_entry_cookies(c))
    if not jar:
        return None
    return "; ".join(f"{k}={v}" for k, v in jar.items()), store.get("ua", "")


def forget(url: str) -> None:
    """Drop the stored cookie for url's host (it stopped working)."""
    store = load_store()
    host = (urlsplit(url).hostname or "").lower()
    for domain in [d for d in store["cookies"] if _domain_matches(host, d)]:
        del store["cookies"][domain]
    save_store(store)


# ---------------------------------------------------------------------------
# Chrome over the DevTools protocol
# ---------------------------------------------------------------------------

def _chrome_binary() -> str:
    for c in CHROME_CANDIDATES:
        if os.path.isabs(c) and os.path.exists(c):
            return c
        if not os.path.isabs(c) and shutil.which(c):
            return c
    raise ClearanceError(
        "Google Chrome not found — install it (https://www.google.com/chrome/) or "
        "add its path to CHROME_CANDIDATES in scripts/cf_clearance.py")


class _CDP:
    """Minimal DevTools client: one browser websocket, flat sessions."""

    def __init__(self, ws_url: str):
        try:
            import websocket  # websocket-client
        except ImportError as e:
            raise ClearanceError("pip install websocket-client (needed to drive Chrome)") from e
        self.ws = websocket.create_connection(ws_url, suppress_origin=True, timeout=60)
        self._id = 0

    def send(self, method: str, params: dict | None = None, session: str | None = None) -> dict:
        self._id += 1
        msg = {"id": self._id, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        self.ws.send(json.dumps(msg))
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == self._id:
                if "error" in r:
                    raise ClearanceError(f"CDP {method}: {r['error']}")
                return r.get("result", {})

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:
            pass


def _launch_chrome(port: int) -> tuple[subprocess.Popen, dict]:
    binary = _chrome_binary()
    prof = profile_dir()
    prof.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [binary, f"--user-data-dir={prof}", f"--remote-debugging-port={port}",
         "--no-first-run", "--no-default-browser-check", "--window-size=1200,900",
         "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    version = None
    for _ in range(80):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
                version = json.load(r)
            break
        except Exception:
            time.sleep(0.25)
    if version is None:
        proc.terminate()
        raise ClearanceError(f"Chrome did not open its DevTools port {port} "
                             f"(another Chrome on that port? set LNGCT_CDP_PORT)")
    return proc, version


def _is_challenge_title(title: str) -> bool:
    t = (title or "").lower()
    return not t or any(f in t for f in CHALLENGE_TITLES)


def _is_challenge_body(html: str) -> bool:
    h = (html or "")[:20000].lower()
    return not h.strip() or any(m in h for m in CHALLENGE_BODY_MARKERS)


def _page_html(cdp: "_CDP", session: str) -> str:
    """Rendered document via the DOM domain (no Runtime.enable)."""
    try:
        root = cdp.send("DOM.getDocument", {"depth": 0}, session=session)["root"]
        return cdp.send("DOM.getOuterHTML", {"nodeId": root["nodeId"]}, session=session)["outerHTML"]
    except ClearanceError:
        return ""


def merge_cookies(store: dict, cookies: list[dict], ua: str, now: float | None = None) -> int:
    """
    Merge the browser's cookie list (DevTools Storage.getCookies shape) into the
    store, keeping only bot-wall cookies, grouped by domain. Session cookies
    (no expiry) get 30 minutes. Returns the number of cookies kept.
    """
    now = time.time() if now is None else now
    store["ua"] = ua or store.get("ua", "")
    by_domain: dict[str, dict] = {}
    for c in cookies:
        name, value = c.get("name", ""), c.get("value", "")
        if not (value and is_wall_cookie(name)):
            continue
        exp = float(c.get("expires") or 0)
        exp = exp if exp > now else now + 1800
        e = by_domain.setdefault(c["domain"], {"cookies": {}, "expires": 0.0, "saved": now})
        e["cookies"][name] = value
        e["expires"] = max(e["expires"], exp)
    kept = 0
    for domain, e in by_domain.items():
        store.setdefault("cookies", {})[domain] = e
        kept += len(e["cookies"])
    return kept


def refresh(urls: list[str], wait: int = 60, port: int = CDP_PORT) -> dict:
    """
    Open each URL in a real Chrome, wait for its bot challenge to clear (title
    no longer a challenge title — a real 404 counts as cleared), harvest every
    bot-wall cookie the browser now holds and merge them into the store.
    Returns the store. Raises ClearanceError when Chrome is missing,
    the browser is forbidden (LNGCT_NO_BROWSER), or no URL cleared.
    """
    if not browser_allowed():
        raise ClearanceError("browser launch forbidden by LNGCT_NO_BROWSER")
    proc, version = _launch_chrome(port)
    cdp = _CDP(version["webSocketDebuggerUrl"])
    cleared: list[str] = []
    try:
        for url in urls:
            tid = cdp.send("Target.createTarget", {"url": url})["targetId"]
            session = cdp.send("Target.attachToTarget", {"targetId": tid, "flatten": True})["sessionId"]
            title = ""
            deadline = time.time() + wait
            while time.time() < deadline:
                time.sleep(2.5)
                info = [t for t in cdp.send("Target.getTargets")["targetInfos"]
                        if t["targetId"] == tid]
                title = info[0]["title"] if info else ""
                page_url = info[0].get("url", "") if info else ""
                if title and title in (page_url, page_url.split("://", 1)[-1]):
                    title = ""                       # untitled page: Chrome shows the URL
                if _is_challenge_title(title) and _is_challenge_body(_page_html(cdp, session)):
                    continue
                cleared.append(url)
                break
            print(f"  [cf_clearance] {url} -> {title!r}", file=sys.stderr)
            cdp.send("Target.closeTarget", {"targetId": tid})
        cookies = cdp.send("Storage.getCookies").get("cookies", [])
    finally:
        cdp.close()
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    store = load_store()
    merge_cookies(store, cookies, version.get("User-Agent", ""))
    save_store(store)
    if not cleared:
        raise ClearanceError("no URL cleared the challenge within the wait "
                             f"({wait}s) — is the site down, or the network captive?")
    return store


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("urls", nargs="*", help="URLs whose bot challenge to clear")
    p.add_argument("--show", action="store_true", help="print the stored cookies and exit")
    p.add_argument("--wait", type=int, default=60, help="seconds to wait per URL")
    args = p.parse_args()
    store = load_store()
    if args.show or not args.urls:
        print(f"store: {store_path()}")
        print(f"ua: {store.get('ua') or '(none)'}")
        for d, c in sorted(store.get("cookies", {}).items()):
            left = c.get("expires", 0) - time.time()
            names = ", ".join(sorted(_entry_cookies(c)))
            print(f"  {d:36s} expires in {left/86400:6.1f} d  {names}")
        if not args.urls:
            return
    try:
        store = refresh(args.urls, wait=args.wait)
    except ClearanceError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"stored {len(store['cookies'])} cookie(s) in {store_path()}")


if __name__ == "__main__":
    main()
