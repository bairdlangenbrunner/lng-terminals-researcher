#!/usr/bin/env python3
"""
gem_export_via_web.py — Download "all-fields" CSV exports from the running
GEM project-database website.

Authentication is by Django session cookie. The site uses Google SSO via
django-allauth; there is no API-token mechanism. One-time setup:

  1. Log into the site in your browser.
  2. DevTools → Application → Cookies → copy `sessionid` and `csrftoken`.
  3. Export three env vars:

       export GEM_PROJECT_DB_BASE_URL='https://gem-project-db.herokuapp.com'
       export GEM_PROJECT_DB_SESSIONID='...'
       export GEM_PROJECT_DB_CSRFTOKEN='...'

  (BASE_URL is optional; defaults to the Heroku host.)

Usage:

  python gem_export_via_web.py lng         -o terminals.csv   # "All LNG CSV"      (115 cols)
  python gem_export_via_web.py lng_export  -o lng-export.csv  # "LNG Export"       (shorter)
  python gem_export_via_web.py goget       -o goget.csv       # "All GOGET"
  python gem_export_via_web.py gogpt       -o gogpt.csv       # "GOGPT All fields" (gas/oil power plants)
  python gem_export_via_web.py both                           # lng + goget, timestamped
  python gem_export_via_web.py all                            # all four, timestamped

The script flips your user's projectType setting (POST /) and then GETs
/units.csv/?format=<name>[&tracker=GOGPT for gogpt]. When the session
expires it prints a clear message — go re-copy the cookies and retry.
"""

import argparse
import datetime
import os
import sys
import urllib.parse

import requests


DEFAULT_BASE_URL = "https://gem-project-db.herokuapp.com"

EXPORTS = {
    # name           projectType id  ?format=...     extra query params           default filename
    "lng":           {"id": 8, "format": "all_lng",    "extra": {},                "default_filename": "lng-all-fields.csv"},
    "lng_export":    {"id": 8, "format": "lng_export", "extra": {},                "default_filename": "lng-export.csv"},
    "goget":         {"id": 9, "format": "all_goget",  "extra": {},                "default_filename": "goget-all-fields.csv"},
    # GOGPT is a sub-tracker of combustion (projectType=1) filtered by trackerSearch.
    "gogpt":         {"id": 1, "format": "gas_all",    "extra": {"tracker": "GOGPT"}, "default_filename": "gogpt-all-fields.csv"},
}


def _make_session(base_url):
    sid = os.environ.get("GEM_PROJECT_DB_SESSIONID")
    csrf = os.environ.get("GEM_PROJECT_DB_CSRFTOKEN")
    if not sid or not csrf:
        missing = []
        if not sid:
            missing.append("GEM_PROJECT_DB_SESSIONID")
        if not csrf:
            missing.append("GEM_PROJECT_DB_CSRFTOKEN")
        sys.exit(
            f"ERROR: missing env var(s): {', '.join(missing)}.\n"
            "\n"
            f"  1. Log into {base_url} in your browser.\n"
            "  2. Open DevTools → Application → Cookies and copy the values\n"
            "     of `sessionid` and `csrftoken`.\n"
            "  3. For THIS shell only, run:\n"
            "\n"
            "       export GEM_PROJECT_DB_SESSIONID='PASTE_SESSIONID_HERE'\n"
            "       export GEM_PROJECT_DB_CSRFTOKEN='PASTE_CSRFTOKEN_HERE'\n"
            "\n"
            "  4. To make them PERMANENT (every new terminal), append the two\n"
            "     `export` lines above to your shell profile, e.g.:\n"
            "\n"
            "       cat >> ~/.zshrc <<'EOF'\n"
            "       export GEM_PROJECT_DB_SESSIONID='PASTE_SESSIONID_HERE'\n"
            "       export GEM_PROJECT_DB_CSRFTOKEN='PASTE_CSRFTOKEN_HERE'\n"
            "       EOF\n"
            "\n"
            "     Then reload with:   source ~/.zshrc\n"
            "\n"
            "  Note: cookies expire periodically — when they do, repeat steps\n"
            "  1-2 and replace the values in ~/.zshrc."
        )

    s = requests.Session()
    host = urllib.parse.urlparse(base_url).hostname
    s.cookies.set("sessionid", sid, domain=host, path="/")
    s.cookies.set("csrftoken", csrf, domain=host, path="/")
    return s


def _check_not_redirected_to_login(resp):
    """Detect the django-allauth login redirect (= dead session)."""
    final = resp.url or ""
    if "/accounts/" in final or "/login" in final:
        sys.exit(
            "ERROR: authentication failed — session cookie is expired or "
            "invalid.\n"
            "  Log into the site in your browser, copy a fresh `sessionid` "
            "and `csrftoken`,\n"
            "  re-export the env vars, and retry."
        )


def _set_project_type(session, base_url, project_type_id):
    csrf = session.cookies.get("csrftoken")
    resp = session.post(
        base_url + "/",
        data={"projectType": project_type_id, "csrfmiddlewaretoken": csrf},
        headers={
            "X-CSRFToken": csrf,
            # Django's CSRF middleware enforces Referer on HTTPS POSTs.
            "Referer": base_url + "/",
        },
        allow_redirects=True,
        timeout=30,
    )
    resp.raise_for_status()
    _check_not_redirected_to_login(resp)


def _download_csv(session, base_url, fmt, extra, out_path):
    params = {"format": fmt, **(extra or {})}
    url = base_url + "/units.csv/?" + urllib.parse.urlencode(params)
    with session.get(url, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        _check_not_redirected_to_login(resp)
        ctype = resp.headers.get("Content-Type", "")
        if "csv" not in ctype.lower():
            sys.exit(
                f"ERROR: expected CSV response, got Content-Type={ctype!r}.\n"
                f"  First 200 chars of body: {resp.text[:200]!r}"
            )
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)


def _export_one(session, base_url, project_type_name, out_path):
    info = EXPORTS[project_type_name]
    print(f"[{project_type_name}] switching projectType → {info['id']}", file=sys.stderr)
    _set_project_type(session, base_url, info["id"])
    extra_str = "".join(f"&{k}={v}" for k, v in info.get("extra", {}).items())
    print(f"[{project_type_name}] GET /units.csv/?format={info['format']}{extra_str} → {out_path}",
          file=sys.stderr)
    _download_csv(session, base_url, info["format"], info.get("extra"), out_path)
    sz = os.path.getsize(out_path)
    print(f"[{project_type_name}] wrote {out_path} ({sz:,} bytes)", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Download all-fields CSV exports from the GEM project DB website."
    )
    parser.add_argument(
        "which",
        choices=["lng", "lng_export", "goget", "gogpt", "both", "all"],
        help=(
            "Which export to download. `lng` = 'All LNG CSV' (115 cols); "
            "`lng_export` = the shorter 'LNG Export' format; "
            "`goget` = 'All GOGET' CSV; "
            "`gogpt` = 'GOGPT All fields' (gas/oil power plants, combustion+tracker=GOGPT); "
            "`both` = lng + goget; "
            "`all` = lng + lng_export + goget + gogpt."
        ),
    )
    parser.add_argument(
        "-o", "--output",
        help="Output filename (single-mode only; ignored for `both`/`all`).",
    )
    args = parser.parse_args()

    base_url = os.environ.get("GEM_PROJECT_DB_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    session = _make_session(base_url)

    multi = {"both": ("lng", "goget"), "all": ("lng", "lng_export", "goget", "gogpt")}
    if args.which in multi:
        ts = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S")
        for name in multi[args.which]:
            base = EXPORTS[name]["default_filename"].rsplit(".", 1)[0]
            _export_one(session, base_url, name, f"{base}-{ts}.csv")
    else:
        out = args.output or EXPORTS[args.which]["default_filename"]
        _export_one(session, base_url, args.which, out)


if __name__ == "__main__":
    main()
