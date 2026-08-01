# BetterMP3

![alt text](https://github.com/Alexs-robotics/BetterMP3/blob/main/GUIPreview.png)

## Features

- **Automatic library**: reads every track from Windows' default
  `Music` folder (or any folder you choose).
- **Grouped by folder**: tracks are organized based on the physical
  folder they live in on disk (not the ID3 "album" tag, which can be
  inconsistent or missing). Each folder is treated as an "album" in
  the main view.
- **Folder/album playback**: select a folder and play it in full,
  ordered by track number.
- **Edit track number**: change a song's order "#" within its folder,
  writing directly to the file's ID3 tag (persistent — it stays even
  if you open the file in another player).
- **Music recommendations**: for the selected track, the app suggests
  similar songs via **Last.fm** (see below for why not Spotify), lets
  you listen to a **30-second preview** from YouTube, and if you like
  it, **download the full track** into
  `downloads/albums/<album name>/` or `downloads/singles/`. Library
  playback automatically pauses when a preview starts, to avoid audio
  overlap.
- **Advanced playback controls**: play/pause, previous/next track,
  adjustable speed (0.75x–2x), a draggable seek bar to jump to any
  point in the track, volume control.
  
## Why Last.fm instead of Spotify?

The project was originally meant to use Spotify's "Recommendations"
endpoint, but **Spotify disabled it for all new apps starting November
27, 2024** (along with Audio Features and Related Artists), with no
way to get it reinstated. Last.fm offers equivalent APIs
(`track.getSimilar`, `artist.getSimilar`) that are free and still
active.

## Installation (development)

1. Install **Python 3.12** (recommended — very recent versions like
   3.14 can have compatibility issues with PySide6/PyInstaller).
   Download it from [python.org/downloads](https://www.python.org/downloads/),
   checking "Add python.exe to PATH" during installation. Avoid the
   Microsoft Store version: it uses very long paths and is more prone
   to package-installation errors on Windows.
2. Install [VLC media player](https://www.videolan.org/vlc/) (64-bit —
   it must match Python's architecture, almost certainly 64-bit) — this
   provides the `libvlc` DLLs used by the playback engine.
3. Install **ffmpeg** and make sure `ffmpeg.exe` is on your system
   PATH (needed by yt-dlp to convert/trim audio):
   ```
   winget install ffmpeg
   ```
   then restart your terminal and check with `ffmpeg -version`.
4. If your Windows system doesn't have long paths enabled and you run
   into package-installation errors, run this in PowerShell as
   administrator:
   ```powershell
   New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
   ```
   then restart your PC.
5. In the project folder:
   ```
   pip install -r requirements.txt
   ```
6. Create a free API key at https://www.last.fm/api/account/create
   and set it in `core/config.py` (the `LASTFM_API_KEY` variable) or
   as an environment variable `LASTFM_API_KEY`.
7. Launch the app:
   ```
   python main.py
   ```


### Spotify API Setup (Premium Only)

If you have a Spotify Premium account, you can enable the **Sync Spotify Liked Songs** feature. This allows the app to read your "Liked Songs" directly from your Spotify library and download them via YouTube into your local music folder.

To set this up:

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Log in with your Spotify Premium account and click **Create app**.
3. Fill in the required details (App name, App description).
4. For the **Redirect URI**, you **must** enter exactly: `http://127.0.0.1:8888/callback`
5. Click **Save** to create the app.
6. Open your new app's dashboard and go to **Settings**.
7. Copy your **Client ID** and **Client Secret**.
8. Open `core/config.py` in this project and paste your credentials into the `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` variables, or set them as environment variables on your system.

**Note:** The first time you use the sync feature, a browser window will open asking you to log in to Spotify and authorize the app. A token will be cached locally (`.spotify_token_cache`) so you don't need to log in every time.

## Building the .exe

Run `build_exe.bat` (from a Windows command prompt, after completing
the installation above). The script automatically bundles the VLC DLLs
into the executable. The result will be in `dist\MP3Player.exe`.

If VLC is installed in a different path than the default, update the
paths inside `build_exe.bat` accordingly.

**Important**: if you edit the source code (`.py` files) while
testing, you don't need to rebuild the exe — just rerun
`python main.py`. Only rebuild the exe when you want the final package
to use or distribute.

## Project structure

```
mp3_player/
├── main.py                        # entry point, applies the theme
├── requirements.txt
├── build_exe.bat                  # builds the .exe
├── core/
│   ├── config.py                  # paths and API keys
│   ├── database.py                # SQLite library cache (grouped by folder)
│   ├── library.py                 # Music folder scanning
│   ├── metadata.py                # ID3 tag reading/writing (incl. track number)
│   ├── net_errors.py              # error messages
│   └── player.py                  # playback engine (python-vlc)
├── services/
│   ├── lastfm_service.py          # similar tracks via Last.fm
│   └── youtube_service.py         # search + preview + download via yt-dlp
│   └── spotify_service.py         # find liked songs through spotify API + download via yt-dlp
└── gui/
    ├── theme.py                   # black/purple Qt stylesheet
    ├── main_window.py             # main window, ties everything together
    ├── album_view.py              # folder/track list + reorder tracks
    ├── player_controls.py         # play/pause/skip/speed/seek
    ├── search_panel.py            # search & download new songs
    ├── spotify_panel.py           # sync spotify liked songs
    ├── track_editor_dialog.py     # track number edit dialog
    └── recommendations_panel.py   # recommendations panel + preview + download
```

## Troubleshooting

- **"No module named pyinstaller" even though `pip list` shows it**:
  usually a mismatch between multiple Python installations. Check with
  `where python` and `pip show pyinstaller` (the `Location` field) that
  they point to the same folder; if needed, reinstall with
  `pip uninstall pyinstaller -y && pip install pyinstaller --no-cache-dir`.
- **`%1 is not a valid Win32 application` when launching the exe**:
  VLC's architecture doesn't match Python's (32 vs 64-bit). Reinstall
  VLC in the 64-bit version.
- **`ffmpeg is not installed`**: see step 3 above.
- **Titles/track numbers still wrong after an update**: click the
  "Full re-read (ignore cache)" button in the app — otherwise the
  cache skips files that haven't changed on disk and keeps showing
  the old values.

## Important legal note

The YouTube download feature should only be used for content you have
the right to download (royalty-free material, your own uploads,
tracks where local law permits it, etc.). Downloading copyrighted
music without authorization may violate YouTube's Terms of Service
and the copyright laws applicable in your jurisdiction.
