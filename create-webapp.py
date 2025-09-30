#!/usr/bin/env python3
import argparse
import os
import re
import sys
import shutil
import pathlib
import imghdr
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

try:
    from PIL import Image
    PIL_OK = True
except Exception:
    PIL_OK = False

HOME = pathlib.Path.home()
APP_DIR = HOME / ".local" / "share" / "applications"
ICON_DIR = HOME / ".local" / "share" / "icons" / "webapps"
PROFILE_BASE = HOME / ".cache" / "ChromiumWebApps"

def slugify(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", name).strip().lower()
    s = re.sub(r"[\s_-]+", "-", s)
    return s or "webapp"

def pick_best_icon_links(soup: BeautifulSoup, base_url: str):
    # Collect rel=icon and apple-touch-icon candidates
    rel_icons = []
    for link in soup.find_all("link"):
        rel = link.get("rel", [])
        href = link.get("href")
        if not href:
            continue
        rel_lower = [r.lower() for r in rel] if isinstance(rel, list) else [str(rel).lower()]
        if any(r in {"icon", "shortcut icon", "apple-touch-icon", "apple-touch-icon-precomposed", "mask-icon"} for r in rel_lower):
            sizes_attr = link.get("sizes", "")
            size_val = 0
            if sizes_attr and sizes_attr != "any":
                # parse like "16x16 32x32"
                try:
                    size_val = max(int(x.split("x")[0]) for x in sizes_attr.split() if "x" in x)
                except Exception:
                    size_val = 0
            href_abs = urljoin(base_url, href)
            rel_icons.append((size_val, href_abs))
    # Sort largest first
    rel_icons.sort(key=lambda x: x[0], reverse=True)
    return [u for _, u in rel_icons]

def find_og_image(soup: BeautifulSoup, base_url: str):
    meta = soup.find("meta", attrs={"property": "og:image"}) or soup.find("meta", attrs={"name": "og:image"})
    if meta and meta.get("content"):
        return urljoin(base_url, meta["content"])
    return None

def fetch(url, session: requests.Session, timeout=15):
    r = session.get(url, timeout=timeout, allow_redirects=True, headers={"User-Agent": "webappify/1.0"})
    r.raise_for_status()
    return r

def discover_icon_urls(page_url: str, session: requests.Session):
    try:
        r = fetch(page_url, session)
    except Exception:
        # Later try /favicon.ico fallback
        return [], None, page_url
    final_url = r.url
    soup = BeautifulSoup(r.text, "html.parser")
    rel_candidates = pick_best_icon_links(soup, final_url)
    og = find_og_image(soup, final_url)
    candidates = []
    candidates.extend(rel_candidates)
    if og:
        candidates.append(og)
    # Always include /favicon.ico fallback
    root = f"{urlparse(final_url).scheme}://{urlparse(final_url).netloc}"
    candidates.append(urljoin(root, "/favicon.ico"))
    # De-duplicate while preserving order
    seen = set()
    uniq = []
    for c in candidates:
        if c not in seen:
            uniq.append(c)
            seen.add(c)
    return uniq, soup.title.string.strip() if soup.title else None, final_url

def ensure_dirs():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_BASE.mkdir(parents=True, exist_ok=True)

def save_icon_from_url(url: str, dest_stem: pathlib.Path, session: requests.Session, size_px: int = 256):
    r = fetch(url, session)
    content = r.content
    # Guess image type
    kind = imghdr.what(None, h=content)
    # Allow SVG by sniffing
    if not kind and (content.strip().startswith(b"<svg") or b"<svg" in content[:200].lower()):
        svg_path = dest_stem.with_suffix(".svg")
        svg_path.write_bytes(content)
        return svg_path
    # For other types, try Pillow to normalize to PNG
    if not PIL_OK:
        # Fallback: write raw and hope DE can read it
        ext = f".{kind}" if kind else ".ico"
        raw_path = dest_stem.with_suffix(ext)
        raw_path.write_bytes(content)
        return raw_path
    from io import BytesIO
    try:
        img = Image.open(BytesIO(content)).convert("RGBA")
    except Exception:
        # As last resort, just write bytes
        ext = f".{kind}" if kind else ".ico"
        raw_path = dest_stem.with_suffix(ext)
        raw_path.write_bytes(content)
        return raw_path
    # Center-crop to square then resize
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img = img.resize((size_px, size_px), Image.LANCZOS)
    out = dest_stem.with_suffix(".png")
    img.save(out, format="PNG")
    return out

def write_desktop_file(path: pathlib.Path, name: str, exec_cmd: str, icon_path: pathlib.Path, categories: str):
    contents = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={name}
Comment={name}
Exec={exec_cmd}
Icon={icon_path}
Terminal=false
Categories={categories}
StartupNotify=true
"""
    path.write_text(contents, encoding="utf-8")

def build_exec(browser_cmd: str, url: str, wm_class: str = None, profile_dir: pathlib.Path = None, wayland: bool = True):
    parts = [browser_cmd, f"--new-window", f"--app={url}"]
    if wayland:
        parts.append("--ozone-platform=wayland")
    if wm_class:
        parts.append(f"--class={wm_class}")
    if profile_dir:
        profile_dir.mkdir(parents=True, exist_ok=True)
        parts.append(f"--user-data-dir={str(profile_dir)}")
    return " ".join(parts)

def main():
    parser = argparse.ArgumentParser(description="Create a .desktop webapp and fetch its icon.")
    parser.add_argument("--name", required=False, help="App display name; defaults to page title or domain")
    parser.add_argument("--url", required=True, help="Website URL")
    parser.add_argument("--browser", default=os.environ.get("WEBAPP_BROWSER", "chromium"), help="Browser command (default: chromium)")
    parser.add_argument("--class", dest="wm_class", default=None, help="WM_CLASS to set for the window")
    parser.add_argument("--isolated", action="store_true", help="Use per-app profile dir (~/.cache/ChromiumWebApps/<slug>)")
    parser.add_argument("--profile-dir", default=None, help="Explicit profile dir for --user-data-dir")
    parser.add_argument("--icon-size", type=int, default=256, help="Icon size in px (default 256)")
    parser.add_argument("--categories", default="Network;", help="Desktop menu categories (default Network;)")
    parser.add_argument("--filename", default=None, help="Override desktop file name (without extension)")
    parser.add_argument("--no-wayland", action="store_true", help="Do not add Wayland flag")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    ensure_dirs()

    session = requests.Session()
    icon_candidates, page_title, final_url = discover_icon_urls(args.url, session)

    # Decide display name
    disp_name = args.name
    if not disp_name:
        if page_title:
            disp_name = page_title
        else:
            disp_name = urlparse(final_url).netloc

    slug = slugify(disp_name if disp_name else "webapp")
    desktop_basename = args.filename or f"webapp-{slug}"
    desktop_path = APP_DIR / f"{desktop_basename}.desktop"

    # Icon
    icon_stem = ICON_DIR / slug
    icon_path = None
    for cand in icon_candidates:
        try:
            icon_path = save_icon_from_url(cand, icon_stem, session, size_px=args.icon_size)
            break
        except Exception:
            continue
    if icon_path is None:
        # last fallback: copy nothing, use generic
        # but DEs accept absolute icon paths; keep None -> skip writing
        pass

    # Profile dir
    profile_dir = None
    if args.profile_dir:
        profile_dir = pathlib.Path(args.profile_dir).expanduser()
    elif args.isolated:
        profile_dir = PROFILE_BASE / slug

    # WM_CLASS default to slug capitalized if not provided
    wm_class = args.wm_class or re.sub(r"[^A-Za-z0-9]", "", slug.title())

    exec_cmd = build_exec(
        browser_cmd=args.browser,
        url=final_url,
        wm_class=wm_class,
        profile_dir=profile_dir,
        wayland=not args.no_wayland
    )

    if desktop_path.exists() and not args.force:
        print(f"{desktop_path} already exists; use --force to overwrite", file=sys.stderr)
        sys.exit(1)

    write_desktop_file(
        path=desktop_path,
        name=disp_name,
        exec_cmd=exec_cmd,
        icon_path=icon_path if icon_path else pathlib.Path("/usr/share/pixmaps/gnome-globe.png"),
        categories=args.categories,
    )

    print(f"Installed: {desktop_path}")
    if icon_path:
        print(f"Icon:      {icon_path}")
    if profile_dir:
        print(f"Profile:   {profile_dir}")

if __name__ == "__main__":
    main()
