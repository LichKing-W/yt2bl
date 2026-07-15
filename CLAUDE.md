# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube to Bilibili video transfer tool for computer science content. The project searches YouTube for CS-related videos, downloads them, processes/format-converts them, and uploads to Bilibili with content localization (Chinese titles, descriptions, tags).

**Tech Stack**: Python 3.9+ (3.13 preferred), yt-dlp, bilibili-api-python, asyncio, Rich CLI, Pydantic, OpenAI API (optional, for subtitle translation).

**Project Type**: CLI tool installed via `pip install -e .` with entry point `yt2bl`

## Current Development Status

**Recently Completed**:
- Full end-to-end workflow: download → translate subtitles → embed bilingual subtitles → upload
- Two-step workflow: `--prepare` (stops before upload) + `--upload-folder` (uploads prepared folder)
- LLM-based subtitle translation with format validation, retry logic, and resume capability (via translation cache)
- LLM-based Chinese title generation from video descriptions
- Bilingual subtitle embedding (English + Chinese) with ASS format support
- Video description and tag generation from translated subtitles
- **Subscription monitor as a one-shot, cron/timer-driven tool** (run periodically via crontab or systemd timer)
- **Watchdog process** (`scripts/monitor_subscription.py`) that kills hung monitor runs and clears the `.updating` lock
- Translation cache system for resuming interrupted subtitle translations
- Automatic `data/` cleanup when more than 10 processed video folders accumulate

## Architecture

```
src/
├── youtube/          # YouTube integration (search, download, models)
├── bilibili/         # Bilibili integration (upload, content optimization)
├── core/             # Video/subtitle processing (FFmpeg-based)
├── utils/            # Config, logging
├── subscription_monitor.py  # One-shot subscription monitor (cron/timer driven)
└── main.py          # CLI entry point with YouTubeToBilibili class
```

**Key Patterns**:
- **Async/await**: All I/O operations use asyncio
- **Progressive enhancement**: Rich library is optional (fallback to plain text); YouTube API is optional (mock data fallback)
- **Modular design**: Each module (searcher, downloader, uploader) works independently

## Development Commands

**Setup**:
```bash
# Standard installation (requires virtual environment)
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"  # Include dev dependencies
# Optional extras:
pip install -e ".[video]"    # For MoviePy video processing
pip install -e ".[bilibili]" # For Bilibili upload
pip install -e ".[translate]" # For subtitle translation via OpenAI

# Alternative: Development mode (run without full install)
# See INSTALL_GUIDE.md for details
./scripts/run_dev.sh
```

**Running**:
```bash
python -m src.main --max-videos 5
python -m src.main --url "https://youtube.com/watch?v=ID"
python -m src.main --channel-id "@username"  # Download from channel (@username, UC...ID, or full URL)
yt2bl --max-videos 3    # After pip install -e .
```

**Complete End-to-End Workflow**:
```bash
# One command to do everything: download, translate, embed subtitles, upload
python -m src.main --full-workflow "https://youtube.com/watch?v=VIDEO_ID"
# Or:
yt2bl --full-workflow "https://youtube.com/watch?v=VIDEO_ID"
```
`run_full_workflow()` (`src/main.py`) runs these steps (display labels are `步骤 1/5` … `5/5`):
1. **Download** video, English subtitles, and thumbnail to `data/{author}|{video_id}/`
2. **Translate subtitles**: preprocess + LLM translation → produces `zh.srt` (bilingual English+Chinese)
3. **Embed bilingual subtitles** into the video (uses `zh.srt`; prefers `{title}_original.mp4` as input so embedding is idempotent)
4. **Upload to Bilibili** — at this point `content_optimizer.optimize_for_bilibili()` runs and:
   - finds the cover image, loads `video_description.txt` (generated from `zh.srt`)
   - generates the **Chinese title** and **Bilibili tags** via LLM
   - uploads as a repost (`copyright=2`, `source` = YouTube URL, `repost_desc` declaration)
5. **Complete**: on success, **adds the video ID to subscription history** (prevents re-processing) and **runs `_cleanup_data_folder()`** (deletes all `data/{author}|{video_id}` folders if more than 10 exist)

> Note: title/tag/description generation happens at upload time (step 4), **after** subtitle embedding (step 3). The full-workflow does not pre-generate the description file; `--prepare` does.

**Two-Step Workflow (Prepare + Upload)**:
```bash
# Step 1: Prepare (download, translate, embed, generate description) - stops before upload
python -m src.main --prepare "https://youtube.com/watch?v=VIDEO_ID"

# Step 2: Upload from prepared folder
python -m src.main --upload-folder "ChannelName|VIDEO_ID"
```
The `--prepare` command (`run_prepare_only`) completes everything EXCEPT uploading:
- Downloads video, subtitles, and thumbnail to `data/{author}|{video_id}/`
- Translates subtitles to Chinese (`zh.srt`)
- Fixes bilingual-subtitle timeline overlaps (`fix_subtitle_overlaps`), then embeds them into the video
- Generates `video_description.txt` from the bilingual subtitles
- Outputs the folder name and the `--upload-folder` command at completion
- Note: `--prepare` does **not** generate the Chinese title or Bilibili tags — those are generated at upload time inside `optimize_for_bilibili()`

The `--upload-folder` command (`run_upload_folder`) uploads a prepared video folder to Bilibili:
- Takes the folder name (not full path) under `data/`
- Prefers the embedded video file
- Shows video info, cover image, and description status
- Uploads directly (non-interactive; no confirmation prompt)

**Subtitle Operations**:
```bash
# Translate subtitles (requires OPENAI_API_KEY)
python -m src.main --translate --max-videos 5
python -m src.main --translate-subs path/to/subs.srt  # Standalone translation

# Convert SRT to ASS format (supports bilingual subtitles)
python -m src.main --convert-to-ass path/to/subs.srt

# Embed bilingual subtitles into video
python -m src.main --embed-bilingual video.mp4 bilingual_subs.srt
python -m src.main --translate --embed-subs --max-videos 5  # Translate then embed

# Generate video description from bilingual subtitles
python -m src.main --gen-description bilingual_subs.srt
```

**Upload Operations**:
```bash
# Upload a specific local video (non-interactive; a filename or --all is required)
python -m src.main --upload-local "video_filename.mp4"

# Upload all videos in the data directory
python -m src.main --upload-local --all

# Batch download from author list (TSV format: "author\tmax_videos")
python -m src.main --batch scripts/author_videonum.txt

# Check Bilibili authentication status
python -m src.main --check-auth
```

**Subscription Monitoring**:

The monitor is a **one-shot** tool. Each invocation runs `run_once()` once and exits; scheduling is done externally via crontab or a systemd timer. There are **no** `run`/`once`/`test` subcommands and **no** `--interval` flag.

```bash
# Run a single check (subtitles translated + embedded by default)
python -m src.subscription_monitor

# Disable subtitle translation or embedding for this run
python -m src.subscription_monitor --no-translate --no-embed

# Via the wrapper script (checks .env / youtuber.txt first, then forwards args)
./scripts/run_subscription_monitor.sh
./scripts/run_subscription_monitor.sh --no-embed
```
The subscription monitor (`src/subscription_monitor.py`):
- **Reads channel list from `youtuber.txt`** (one identifier per line: `@username`, `UC...ID`, or full channel URL). It does **not** use YouTube cookies / your subscriptions.
- **Checks for new videos**: gets the latest `VIDEOS_PER_CHANNEL` (hardcoded class constant = 3) videos per channel, compares against history
- **Processes queue**: runs `--full-workflow` for each new video serially (download, translate, embed subtitles, upload)
- **Retry logic**: a failed video is retried once (5s pause), then skipped
- **History tracking**: processed video IDs are saved to `subscription_history.json` (in project root)
  - History is updated automatically by `main.py` after each successful upload (via `_add_to_subscription_history()`)
  - Manual `--full-workflow` runs use the same history file
  - Corrupted JSON history is backed up to `.json.corrupted` and recreated
- **Singleton lock**: writes `.updating` (containing PID + start time) at the start of `run_once()` and removes it in a `finally` block. If `.updating` already exists, the run is skipped to avoid overlapping instances.

**Watchdog (handles stuck monitor runs)**:

Embedding subtitles can occasionally hang and hold the `.updating` lock for hours, blocking later runs. `scripts/monitor_subscription.py` checks the running monitor process and, if it exceeds a timeout (default 6 hours), terminates it (SIGTERM, then SIGKILL after 30s) and deletes `.updating`:

```bash
# Dry-run check (no action)
python scripts/monitor_subscription.py --dry-run

# Check & kill if over threshold
python scripts/monitor_subscription.py            # default 6h
python scripts/monitor_subscription.py --timeout 3
```
The watchdog parses PID/start-time from `.updating`, so the lock file format is `PID: <pid>\nStarted: <iso>\n`.

**Running as a background service**:

The recommended pattern is a **periodic one-shot** (cron or systemd timer) for the monitor, plus the **watchdog** timer.

Option 1: crontab (Linux/macOS):
```bash
cp scripts/crontab.example /tmp/my_crontab
# Edit /tmp/my_crontab: set the correct venv path and schedule
crontab /tmp/my_crontab
crontab -l   # verify
```
```cron
# Monitor — hourly (one-shot; no "run" subcommand)
0 * * * * source /path/to/yt2bl/.venv/bin/activate && python -m src.subscription_monitor >/dev/null 2>&1
# Watchdog — kill stuck runs
0 * * * * source /path/to/yt2bl/.venv/bin/activate && python scripts/monitor_subscription.py >/dev/null 2>&1
```

Option 2: systemd.
- **Monitor (system-level)**: edit & install `scripts/yt2bl-monitor.service.example` into `/etc/systemd/system/`, then enable+start it. Drive it periodically with a `.timer` unit (the example is a long-running `Restart=always` service; for the one-shot model prefer a timer calling the bare `python -m src.subscription_monitor`).
- **Watchdog (user-level)**: run `./scripts/install_systemd.sh`, which installs `yt2bl-monitor-watchdog.{service,timer}` (runs every 10 minutes, `--timeout 6`). Manage with `systemctl --user`.
```bash
sudo systemctl daemon-reload && sudo systemctl enable --now yt2bl-monitor
systemctl --user status yt2bl-monitor-watchdog.timer
sudo journalctl -u yt2bl-monitor -f          # monitor logs
journalctl --user -u yt2bl-monitor-watchdog -f  # watchdog logs
# Keep timers alive after logout:
loginctl enable-linger $USER
```
See `scripts/monitor_README.md` for the watchdog details.

**Testing**:
```bash
pytest test/ -v                    # Run all tests
pytest test/test_specific.py -v    # Single test file
./scripts/quick_test.sh            # Quick test script
```

**Code Quality**:
```bash
ruff check --fix src/              # Lint and auto-fix
ruff format src/                   # Format code
mypy src/                          # Type check
```

## Configuration

Configuration is centralized in `src/utils/config.py` via environment variables. Copy `.env.example` to `.env`:

- `YOUTUBE_API_KEY`: Optional (fallback to mock data if not provided)
- `YOUTUBE_COOKIES_FILE`: Path to YouTube cookies file (Netscape format) to bypass bot detection
- `PROXY`: HTTP/HTTPS proxy for YouTube access (e.g., `http://127.0.0.1:7897`)
- `BILIBILI_SESSDATA`, `BILIBILI_BILI_JCT`, `BILIBILI_DedeUserID`: Required for upload
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`: For subtitle translation (default: gpt-4o-mini)
- `DOWNLOAD_PATH`: Default `./data`
- `MAX_VIDEO_SIZE_MB`, `VIDEO_QUALITY`, `UPLOAD_COOLDOWN_HOURS`, `AUTO_PUBLISH`
- `LOG_LEVEL`, `LOG_FILE`
- `FFMPEG_HWACCEL`: Hardware acceleration for subtitle embedding (auto, nvenc, qsv, amf, videotoolbox, vaapi, none)
- `FFMPEG_PRESET`: Encoder preset for quality/speed balance (fast, medium, slow, etc.)

> Note on subscription settings: `.env.example` lists `SUBSCRIPTION_CHECK_INTERVAL` and `SUBSCRIPTION_VIDEOS_PER_CHANNEL`, but the current `subscription_monitor.py` does **not** read them. The monitor is one-shot (scheduling is external), and `VIDEOS_PER_CHANNEL = 3` is a hardcoded class constant in `SubscriptionMonitor`. Scheduling frequency is controlled by crontab/systemd timer, and the per-channel video count can be changed by editing that constant.

**Proxy Configuration**:

Proxy support is integrated into the Python code via `.env` configuration:

1. **In .env file**: Set the `PROXY` variable
   ```bash
   PROXY=http://127.0.0.1:7897
   ```

2. **Application scope**: The proxy is automatically applied to:
   - All yt-dlp operations (download, search, channel info)
   - YouTube video downloads
   - YouTube channel checks (subscription monitor)

3. **No environment variables needed**: Unlike the old approach, you don't need to set `HTTP_PROXY`/`HTTPS_PROXY` in crontab or systemd. The Python code reads `PROXY` from `.env` and passes it to yt-dlp directly.

**Note**: The old `.env.cron` file is deprecated. Use `PROXY` in `.env` instead.

## Important Implementation Details

1. **CS Content Filtering**: `src/youtube/models.py` contains 87+ computer science keywords for content filtering in `YouTubeVideo.is_cs_content()`

2. **Quality Scoring**: `YouTubeVideo.get_quality_score()` rates videos based on views, engagement, duration

3. **Progress Tracking**: Download operations accept an `update_progress(percent, speed)` callback for Rich progress bars

4. **Error Handling**: Extensive try-catch with graceful degradation. Check `src/main.py` for patterns (RICH_AVAILABLE flag for optional Rich library)

5. **Data Models** (`src/youtube/models.py`):
   - `YouTubeVideo`: Pydantic model representing a YouTube video with metadata
   - `YouTubeSearchResult`: Container for search results with video filtering
   - All models use Pydantic for validation and serialization

6. **SRT Data Structure**: All SRT parsing/processing uses consistent keys:
   - `index`: Subtitle sequence number
   - `start`: Start timestamp (format: `"00:00:00,000"`)
   - `end`: End timestamp
   - `text`: Subtitle text content
   - Important: Never use `start_time`/`end_time` - use `start`/`end` consistently

7. **Fail-Fast Workflow**: All workflows stop immediately on any critical error:
   - Video download failure → stop
   - Subtitle translation failure → stop
   - Subtitle embedding failure → stop
   - Upload failure → stop and report failure
   - This prevents uploading incomplete/incorrect content to Bilibili

8. **Data Folder Cleanup** (`main.py:_cleanup_data_folder`, default `max_folders=10`): after a successful full-workflow upload, if more than 10 `data/{author}|{video_id}` folders exist, **all** of them are deleted. Keep this in mind before leaving lots of prepared folders in `data/`.

9. **Subtitle Processing** (`src/core/subtitle_processor.py`):
   - **LLM-based translation**: Uses LLM API (e.g., OpenAI, DeepSeek) to translate English subtitles to bilingual format
   - `translate_with_openai()`: Full translation pipeline with preprocessing
     - **Batch translation**: Processes 10 subtitles per LLM request (`batch_size = 10`)
     - Parses structured bilingual results: `"1. English text\n1. 中文翻译\n2. English text\n2. 中文翻译\n..."`
     - Supports multiple formats: with or without repeated index numbers, using `.` or `:` separator
     - **Format validation**: Checks if all subtitles contain both English and Chinese, retries up to 5 times (`max_retries = 5`) if format is incorrect
     - Validates translation completeness and fills missing entries with original text
     - **Translation cache**: Automatically saves progress to `{output_path.stem}.cache.json` after each batch
       - Allows resuming from interruption (e.g., network failure, API rate limit)
       - Cache validation: verifies subtitle hash, total count, and batch size match
       - Cache is automatically cleared after successful translation
       - Cache file location: `data/{author}|{video_id}/zh.cache.json`
   - Preprocessing steps: fix timeline overlaps → merge subtitle lines (2:1) → LLM translation
   - **Smart merge algorithm** (`merge_subtitle_lines`): Merges 2 subtitle lines into 1
     - Uses first line's start time and second line's end time
     - Skips merging if combined text has >15 words (uses `_count_words()`)
     - Word counting uses regex `\b[\w-]+\b` to handle punctuation and hyphens
   - `convert_srt_to_ass()`: Converts to ASS format with separate styles for Chinese/English
     - Defaults: `en_font_size=16`, `zh_font_size=20` (embed step uses 36 / 60)
     - **Chinese style**: Source Han Sans CN, white text, dark reddish-brown outline `&H00503129` (Outline=3), larger font, `MarginV = en_font_size + 8` (positioned above English)
     - **English style**: DejaVu Sans, white text, black outline `&H00000000` (Outline=2), `MarginV = 4` (bottom)
     - Separates Chinese and English lines into different Dialogue entries with Layer separation (English Layer=0, Chinese Layer=1)
   - `fix_subtitle_overlaps()`: Adjusts end times to remove overlapping cues; used explicitly by `--prepare` before embedding
   - `embed_subtitles_to_video()`: Hardcodes bilingual subtitles into video using FFmpeg
   - `generate_description_from_subtitle()`: Creates `video_description.txt` from translated subtitles

10. **LLM Prompts** (`prompts/` directory):
    - All prompts are stored as Markdown files for easy editing
    - `translate.md`: Subtitle translation prompt (bilingual English+Chinese)
    - `description.md`: Video description generation prompt
    - `generate_title.md`: Chinese title generation prompt (5-20 characters)
    - `generate_tags.md`: Bilibili tag generation prompt (3-6 tags)
    - Prompts are read at runtime using `Path(__file__).parent.parent / "prompts" / "filename.md"`

11. **File Organization**:
    - Each video gets its own subfolder: `data/{author_name}|{video_id}/`
    - All files for a video (video, bilingual subtitles, descriptions, thumbnail) are stored in its subfolder
    - Example: `data/ChannelName|abc123/video.mp4`, `data/ChannelName|abc123/zh.srt`
    - The YouTuber name is parsed from the folder name at the `|` separator (underscores → spaces)
    - Thumbnails are automatically downloaded and saved as `{video_title}.jpg`
    - **Subtitle files**: Only English subtitles `{title}.en.srt` are downloaded from YouTube
      - Bilingual subtitles `zh.srt` are generated by LLM translation (contains both English and Chinese)
      - Translation cache: `zh.cache.json` (auto-created during translation, auto-deleted after success)
      - Final embedded video: `{title}.mp4` (after subtitle embedding, the pre-embed source is `{title}_original.mp4`)
    - **Bilibili upload settings**: Videos are uploaded as reposts (转载)
      - `copyright=2`: Indicates repost content (not original)
      - `source`: YouTube original video URL
      - `repost_desc`: Repost declaration with channel name
      - Video descriptions come from `video_description.txt`; the YouTube URL is **not** prepended to the description (it lives in `source`/`repost_desc`)
    - **Subscription monitoring**:
      - `youtuber.txt`: Channel list for subscription monitor (one per line)
        - Supports: `@username`, `UC...ID`, or full YouTube channel URLs
        - Empty lines and `#` comments are ignored
      - `subscription_history.json`: Persistent history of processed video IDs (in project root, not data/)
      - `.updating`: Lock file written during a monitor run (format: `PID: <pid>\nStarted: <iso>`)

12. **Author Batch Processing**: `scripts/author_videonum.txt` format is TSV: `channel_id\tmax_videos` (one per line, supports # comments)

13. **YouTube Download Format Handling** (`src/youtube/downloader.py`, `_get_format_selector()`):
    - YouTube uses DASH (separate video/audio streams) for 1080p+.
    - A single yt-dlp selector is built from `VIDEO_QUALITY`: `bestvideo[height<=H]+bestaudio/best[height<=H]/best`
      1. Separate best video + best audio at target height (merged with FFmpeg)
      2. Single file at target height
      3. Any best available format (fallback)
    - Requires FFmpeg installed to merge video/audio streams for 1080p+

14. **Bilibili Content Optimization** (`src/bilibili/content_optimizer.py`):
    - `optimize_for_bilibili()` is the single entry point called at upload time. It:
      1. Extracts the YouTuber name from the folder name
      2. Finds the cover image (`_find_cover_image`)
      3. Loads `video_description.txt` if present (else falls back to a default optimized description)
      4. Generates the **Chinese title** via LLM (`generate_optimized_title`)
      5. Generates **tags** via LLM (`generate_tags`)
      6. Determines the category and builds a `BilibiliVideo` (`copyright=2`, `source` = YouTube URL, `repost_desc`)
    - **LLM-based Chinese title generation** (`prompts/generate_title.md`)
      - Analyzes original English title and video description
      - Title length: 5-20 Chinese characters (max 80 chars)
      - Technical terms may remain in English (e.g., API, dlopen, Python)
      - Appends YouTuber name automatically: "中文标题 | YouTuber名"
      - Falls back to original title if LLM generation fails
    - **LLM-based tag generation** (`prompts/generate_tags.md`): 3-6 Chinese tags from the video description
    - Tag generation hierarchy:
      1. YouTuber name (if available)
      2. LLM-generated tags from video description
      3. YouTube original tags (translated to Chinese if needed)
      4. Hot tag matching (predefined CS-related tags)
      5. Language tags ("英语", "中文") for bilingual content
    - Maximum 12 tags per Bilibili upload (platform limit)
    - **Cover image lookup order**: `cover.jpg` (preferred) → image with the same stem as the video → any image in the folder (`.jpg/.jpeg/.png/.webp`)

15. **Subscription Monitor Architecture** (`src/subscription_monitor.py`):
    - **One-shot design**: `main()` → `run()` → `run_once()` runs a single check cycle and exits. Scheduling is external (crontab/systemd timer). There are no `run`/`once`/`test` subcommands and no `--interval` flag.
    - **CLI flags** (`main()`): only `--no-translate` and `--no-embed`.
    - **Singleton pattern**: `.updating` lock (PID + start time) written at the start of `run_once()` and removed in `finally`. If `.updating` exists, the run is skipped. The watchdog cleans stale locks.
    - **History management**: persistent JSON (`subscription_history.json` in project root)
      - Tracks all processed video IDs across runs
      - Survives process restarts and system reboots
      - Corrupted JSON is backed up as `.json.corrupted` and recreated
    - **Source of channels**: reads `youtuber.txt` (not YouTube cookies). Identifiers normalized to `@handle` or `UC...ID` via `_extract_channel_identifier()`.
    - **Processing workflow** (`run_once()`):
      1. Acquire singleton lock (write `.updating`)
      2. Load channel list from `youtuber.txt`
      3. For each channel, fetch latest `VIDEOS_PER_CHANNEL` (3) videos ordered by date
      4. Filter out already-processed videos (from history)
      5. Process new videos serially via `run_full_workflow()` (retry once on failure)
      6. History is updated automatically by `run_full_workflow()` after each successful upload
      7. Release lock in `finally`

## Code Quality Standards

**Ruff Configuration** (from `pyproject.toml`):
- Line length: 88 characters
- Target Python version: 3.13
- Quote style: double
- Indent style: space
- Enabled rule sets: E, F, W, I, N, B, C90
- Ignored: E501 (line length), B008 (function calls in defaults)

**Type Checking** (mypy):
- Python 3.13 target
- Strict mode: `disallow_untyped_defs = true`
- All new code should include type hints
- Use `Optional[T]` for nullable types

**Testing Configuration** (pytest):
- Test files: `test_*.py` in `test/` directory
- Default options: `-v --tb=short`
- Uses pytest-asyncio for async test support

### Code Style Guidelines

**Import Organization**:
- Group order: standard library → third-party → relative imports
- Use try/except for optional dependencies (e.g., Rich, yt-dlp, Pillow)
- Set availability flags (e.g., `RICH_AVAILABLE = True/False`)
- Example:
```python
import asyncio
from pathlib import Path
from typing import Optional, List

try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from ..utils.logger import logger
```

**Naming Conventions**:
- Classes: PascalCase (`YouTubeToBilibili`, `SubtitleProcessor`)
- Functions/methods: snake_case (`run_full_workflow`, `_parse_srt_file`)
- Private methods: underscore prefix (`_ensure_initialized`)
- Module-level variables: lowercase (`settings`, `logger`)
- Constants: UPPER_SNAKE_CASE (where applicable)

**Async/Await Patterns**:
- All I/O operations must be async (downloads, uploads, file operations)
- Use `asyncio.create_subprocess_exec` for subprocess calls (FFmpeg, etc.)
- Use `asyncio.get_event_loop().run_in_executor()` for blocking operations
- Example:
```python
# Subprocess pattern
process = await asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
stdout, stderr = await process.communicate()

if process.returncode == 0:
    logger.info(f"Operation succeeded")

# Blocking operation pattern
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, self._sync_operation, arg1, arg2)
```

**File Operations**:
- Use `pathlib.Path` for all file operations
- Always specify encoding: `read_text(encoding="utf-8")`, `write_text(..., encoding="utf-8")`
- Use `encoding="utf-8-sig"` for ASS files (UTF-8 with BOM)
- Create directories with `mkdir(parents=True, exist_ok=True)`
- Sanitize filenames to remove illegal characters: `<>:"/\|?*` (keep `|` for folder separators)

## Known Limitations

- YouTube download may require cookies to bypass bot detection (use `YOUTUBE_COOKIES_FILE` in .env)
- YouTube search restricted by anti-bot measures (API key recommended)
- Bilibili upload requires authentication cookies from browser
- Video embedding requires FFmpeg installed and available in PATH
- Subtitle translation requires OpenAI API key (or compatible endpoint) if YouTube auto-translate is unavailable
- mypy type checking is configured for Python 3.13 but project supports Python 3.9+
- `data/` is auto-wiped of all video folders once more than 10 accumulate (see `_cleanup_data_folder`)

## Upload Optimization

When uploading to Bilibili (`content_optimizer.optimize_for_bilibili`), the system automatically:

1. **Uses Generated Description**: If `video_description.txt` exists in the video folder, it's used as the upload description; otherwise a default optimized description is generated.
2. **Finds Cover Image**: `cover.jpg` (preferred) → image named after the video file → any image in the folder (`.jpg/.jpeg/.png/.webp`)
3. **Generates Chinese title & tags** via LLM at upload time.

## Utility Scripts

- **`src/utils/fix_you_srt_tl.py`**: Fixes subtitle timeline overlaps
  - Usage: `python src/utils/fix_you_srt_tl.py <file.srt> [FPS=60]`
  - Adjusts subtitle end times to prevent overlaps by using a 1-frame gap
  - Creates `file_fix.srt` alongside the original
- **`scripts/monitor_subscription.py`**: Watchdog that kills monitor runs exceeding a timeout (default 6h) and removes `.updating`. `--dry-run` / `--timeout H`.
- **`scripts/run_subscription_monitor.sh`**: Wrapper that checks `.env`/`youtuber.txt`/Bilibili config, then runs `python -m src.subscription_monitor "$@"`.
- **`scripts/install_systemd.sh`**: Installs the user-level watchdog service+timer (`yt2bl-monitor-watchdog.*`).

## Unit Tests

The test suite covers critical subtitle processing functionality:

- **`test/test_subtitle_translation.py`**: Tests batch translation workflow
  - SRT file parsing and formatting
  - Batch formatting for LLM (`"1: Text\n2: Text\n..."`)
  - Translation result parsing and completeness validation
  - SRT rebuilding from translated text
  - Full workflow end-to-end test

- **`test/test_translation_cache.py`**: Comprehensive translation cache system tests
  - Cache file creation and persistence
  - Cache path generation (`zh.cache.json` alongside `zh.srt`)
  - Subtitle hash calculation for validation
  - Cache validation (hash, total count, batch size)
  - Cache update mechanism (batch-by-batch saving)
  - Resume from interrupted translation
  - Cache clearing after successful translation

- **`test/test_cache_manual.py`**: Manual testing utilities for cache behavior debugging

- **`test/test_merge_algorithm.py`**: Tests smart subtitle merging (2:1 ratio)
  - Word counting regex (`\b[\w-]+\b`)
  - Merge logic with long combined text (>15 words stay separate)
  - Merge logic with short combined text (normal 2:1 merge)

- **`test/test_chinese_style.py`**: Tests ASS subtitle styling
  - Verifies `Chinese` style definition (Source Han Sans CN, white text, dark reddish-brown outline &H00503129)
  - Confirms Chinese/English lines are separated into different Dialogues with Layer separation
  - Validates ASS file generation with correct styling and positioning

- **`test/test_format_selector.py`**: Tests the yt-dlp format selector (`bestvideo[height<=H]+bestaudio/...`) for correct 1080p selection

- **`test/test_video_processor.py`**: Tests video processing functionality
- **`test/test_youtube_searcher.py`**: Tests YouTube search and video filtering

## Common Workflow Patterns

When working with this codebase, you'll commonly encounter these patterns:

**1. Adding a New CLI Feature**:
- Add the argument to the `argparse` setup in the `cli()` function (`src/main.py`)
- Add a corresponding method to `YouTubeToBilibili` class
- Call the method from the `cli()` dispatch block (below `args = parser.parse_args()`) with proper argument checks
- Update CLAUDE.md if the workflow is significant

**2. Extending Subtitle Processing**:
- All subtitle operations go through `SubtitleProcessor` class (`src/core/subtitle_processor.py`)
- Follow the async/await pattern for I/O operations
- Use consistent SRT data structure: `{"index": int, "start": "HH:MM:SS,mmm", "end": "HH:MM:SS,mmm", "text": str}`
- For LLM operations, prompts are stored in `prompts/` directory
  - `translate.md`: Subtitle translation prompt (bilingual English+Chinese)
  - `description.md`: Video description generation prompt
  - `generate_tags.md`: Bilibili tag generation prompt
  - `generate_title.md`: Chinese title generation prompt

**3. File Naming Conventions**:
- Downloaded videos: `{title}.mp4` (final/embedded), `{title}_original.mp4` (pre-embed source)
- English subtitles from YouTube: `{title}.en.srt`
- Bilingual subtitles (LLM output): `zh.srt`
- Video descriptions: `video_description.txt`
- Cover images: `cover.jpg` (preferred) or any `{title}.{ext}`

**4. Error Handling Pattern**:
```python
try:
    # Operation
    if not success:
        self.console.print("❌ Error message", style="red")
        return  # Stop workflow on critical errors
except Exception as e:
    logger.error(f"Detailed error: {str(e)}")
    self.console.print(f"❌ User-friendly error", style="red")
    import traceback
    logger.error(traceback.format_exc())
```
