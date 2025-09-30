# webappify.py
Turn any website into a seamless Linux desktop app — complete with native launcher icons — using a single command. Automatically discovers & downloads icons, builds .desktop shortcuts for Chromium in app mode, and supports isolated per-site profiles for perfect integration.

## What is this?
**webappify.py** makes “web apps” out of any web site:  
- It generates `.desktop` launchers in `~/.local/share/applications`, so apps show up in menus and hotkeys just like Omarchy and Peppermint ICE.
- It auto-fetches icons — favicon, Apple touch icon, or Open Graph image — so your app entries look polished and recognizable.
- It launches the site in Chromium’s [--app mode](https://chromium.googlesource.com/chromium/src/+/main/docs/user_data_dir.md) (frameless, minimal window) for a truly seamless experience.
- It supports per-app profile isolation (`--user-data-dir`), taskbar grouping (`--class`), and all XDG standards for a first-class experience on Arch, Hyprland, KDE, GNOME, etc.

## Why use it?
- **Works everywhere**: No DE lock-in, integrates with application menus, launchers, and binds beautifully with Hyprland or any Wayland/X11 window manager.
- **Zero manual packaging**: Automatically finds and downloads the highest-quality icons for any site (link rel="icon"/"apple-touch-icon", og:image, favicon fallback).
- **Real multi-account support**: Optionally creates a separate browser profile per app, meaning you can log in to multiple Google/Outlook/work apps side-by-side.
- **Open, inspectable, and easy to extend**.

## Usage

Basic usage: create a Proton Mail desktop app with automatic icon
```python3 webappify.py --url https://mail.proton.me --name "Proton Mail"```

Use a separate browser profile (no shared cookies)
```python3 webappify.py --url https://calendar.google.com --name "Google Calendar" --isolated```

Custom browser (e.g., Brave, Chrome)
```WEBAPP_BROWSER=brave-browser python3 webappify.py --url https://discord.com --name "Discord"```

For X11 (no Wayland flag):
```python3 webappify.py --url https://outlook.office.com --name "Outlook" --no-wayland```

Fine-tune window manager grouping:
```python3 webappify.py --url https://github.com --name "GitHub" --class GitHub```

You get:
- `.desktop` file in `~/.local/share/applications`
- Icon downloaded to `~/.local/share/icons/webapps`
- Optionally: unique Chromium profile per app for multi-account logins

## Features
- **Automatic icon discovery**: Finds the site’s best icon (SVG/PNG/JPG supported), resizes to a square for maximum launcher compatibility.
- **Accurate app naming**: Uses your provided name, page title, or domain name for native-feeling entries.
- **Real isolation**: With `--isolated`, makes every app run in a sandboxed browser profile.
- **Standards compliant**: All launchers follow [freedesktop XDG spec](https://specifications.freedesktop.org/desktop-entry-spec/latest/ar01s03.html) for maximum menu/launcher compatibility.
- **Wayland & X11**: Wayland support enabled by default with `--ozone-platform=wayland` (toggle with `--no-wayland`).

## Requirements
- Python 3.8+
- [requests](https://pypi.org/project/requests/), [beautifulsoup4](https://pypi.org/project/beautifulsoup4/), [pillow](https://pypi.org/project/pillow/)
- Chromium (or another app-mode compatible browser)

Install dependencies:
```pip install --user requests beautifulsoup4 pillow```

## FAQ

**Q: Where are launchers and icons placed?**  
A: Launchers go to `~/.local/share/applications`, icons to `~/.local/share/icons/webapps` (per user, no root needed).

**Q: Can I use Google Chrome, Brave, or any Chromium fork?**  
A: Yes! Just set `--browser` or the environment variable `WEBAPP_BROWSER`.

**Q: How does it pick the icon?**  
A: Tries all the following in order, using the first that works:
- HTML `<link rel="icon">` and variants
- `<link rel="apple-touch-icon">`
- Open Graph `<meta property="og:image">`
- `/favicon.ico` at site root

**Q: Does it work with Hyprland or KDE Plasma?**  
A: Yes. Desktop entries and icons follow XDG conventions and will show up in menus/launchers everywhere.

**Q: Is this secure?**  
A: All downloads are from the target site. Isolated mode keeps cookies/localStorage separate per app.

**Q: Why not just use Chromium’s “Install as app” button?**  
A: This tool gives you full control, works for any site (even without PWA support), and supports per-app isolation and tuner flags Omarchy power-users rely on.

## License

MIT — do whatever you want, just don’t blame the author if the internet breaks.


---
This README describes **webappify.py**, a power tool for Linux power users who want real native-feeling web apps, with automatic icon discovery and full XDG launcher support.
