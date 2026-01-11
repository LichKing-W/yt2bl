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
- LLM-based subtitle translation with format validation and retry logic
- LLM-based Chinese title generation from video descriptions
- Bilingual subtitle embedding (English + Chinese) with ASS format support
- Video description and tag generation from translated subtitles
- Subscription monitoring daemon for automated video transfer from subscribed channels

## Architecture

```
src/
├── youtube/          # YouTube integration (search, download, models)
├── bilibili/         # Bilibili integration (upload, content optimization)
├── core/             # Video/subtitle processing (FFmpeg-based)
├── utils/            # Config, logging
├── subscription_monitor.py  # Subscription monitoring daemon
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
This single command will:
1. Download video, English subtitles, and thumbnail to `data/{author}|{video_id}/`
2. Preprocess subtitles and translate them using LLM
3. Generate video description from translated subtitles (first line is original YouTube URL)
4. Generate Chinese title using LLM
5. Generate Bilibili tags using LLM
6. Create bilingual subtitles and embed into video
7. Upload to Bilibili with cover image, Chinese title, tags, and description
8. **Add video ID to subscription history** (preventing re-processing by subscription monitor)

**Two-Step Workflow (Prepare + Upload)**:
```bash
# Step 1: Prepare (download, translate, embed) - stops before upload
python -m src.main --prepare "https://youtube.com/watch?v=VIDEO_ID"

# Step 2: Upload from prepared folder
python -m src.main --upload-folder "ChannelName_VIDEO_ID"
```
The `--prepare` command completes everything EXCEPT uploading to Bilibili:
- Downloads video, subtitles, and thumbnail to `data/{author}|{video_id}/`
- Translates subtitles to Chinese
- Merges and embeds bilingual subtitles into video
- Generates video description from translated subtitles
- Generates Chinese title and Bilibili tags using LLM
- Outputs the folder name and upload command at completion

The `--upload-folder` command uploads a prepared video folder to Bilibili:
- Takes the folder name (not full path) under `data/`
- Prefers `_embedded` video files if available
- Shows video info, cover image, and description status
- Prompts for confirmation before uploading

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
# Upload local videos interactively
python -m src.main --upload-local

# Upload specific local video
python -m src.main --upload-local "video_filename.mp4"

# Upload all videos in data directory
python -m src.main --upload-local --all

# Batch download from author list (TSV format: "author\tmax_videos")
python -m src.main --batch scripts/author_videonum.txt

# Check Bilibili authentication status
python -m src.main --check-auth
```

**Subscription Monitoring**:
```bash
# Run subscription monitor (continuous mode)
./scripts/run_subscription_monitor.sh run
# Or directly:
python -m src.subscription_monitor run

# Run once (for testing)
./scripts/run_subscription_monitor.sh once
python -m src.subscription_monitor once

# Test mode with verbose output
python -m src.subscription_monitor test

# Custom check interval (default: 3600 seconds = 1 hour)
python -m src.subscription_monitor run --interval 1800

# Disable subtitle translation or embedding
python -m src.subscription_monitor run --no-translate --no-embed
```
The subscription monitor (`src/subscription_monitor.py`):
- **Fetches subscriptions**: Uses YouTube cookies to get your subscribed channels
- **Checks for new videos**: Gets latest 3 videos per channel, compares against history
- **Processes queue**: Downloads, translates, embeds subtitles, uploads to Bilibili serially
- **Retry logic**: Failed videos are retried once, then skipped
- **History tracking**: Processed video IDs are saved to `subscription_history.json` (permanent, in project root)
  - History is updated automatically after each successful upload
  - Manual `--full-workflow` runs also update history
  - Both monitor and manual workflows use the same history file
- **Continuous monitoring**: Checks every hour (configurable) for new videos
- **Singleton lock**: Uses file-based lock (`.updating`) to prevent multiple instances running simultaneously

**Running as a background service**:

Option 1: systemd (Linux):
```bash
# Copy and edit the service file
sudo cp scripts/yt2bl-monitor.service.example /etc/systemd/system/yt2bl-monitor.service
sudo vim /etc/systemd/system/yt2bl-monitor.service  # Update paths (User, WorkingDirectory, ExecStart)

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable yt2bl-monitor
sudo systemctl start yt2bl-monitor
sudo systemctl status yt2bl-monitor
# View logs:
sudo journalctl -u yt2bl-monitor -f
```

Option 2: crontab (Linux/macOS):
```bash
# Copy the crontab example and modify paths
cp scripts/crontab.example /tmp/my_crontab
# Edit /tmp/my_crontab to update paths and set schedule
# Install crontab:
crontab /tmp/my_crontab
# View installed crontab:
crontab -l
```

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
- `FFMPEG_HWACCEL`: Hardware acceleration for subtitle embedding (auto, nvenc, qsv, amf, videotoolbox, vaapi, none)
- `FFMPEG_PRESET`: Encoder preset for quality/speed balance (fast, medium, slow, etc.)
- `SUBSCRIPTION_CHECK_INTERVAL`: Subscription monitor check interval in seconds (default: 3600 = 1 hour)
- `SUBSCRIPTION_VIDEOS_PER_CHANNEL`: Number of recent videos to check per channel (default: 3)

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

8. **Subtitle Processing** (`src/core/subtitle_processor.py`):
   - **LLM-based translation**: Uses LLM API (e.g., OpenAI, DeepSeek) to translate English subtitles to bilingual format
   - `translate_with_openai()`: Full translation pipeline with preprocessing
     - **Batch translation**: Processes 10 subtitles per LLM request
     - Parses structured bilingual results: `"1. English text\n1. 中文翻译\n2. English text\n2. 中文翻译\n..."`
     - Supports multiple formats: with or without repeated index numbers, using `.` or `:` separator
     - **Format validation**: Checks if all subtitles contain both English and Chinese, retries up to 5 times if format is incorrect
     - Validates translation completeness and fills missing entries with original text
   - Preprocessing steps: fix timeline overlaps → merge subtitle lines (2:1) → LLM translation
   - **Smart merge algorithm**: Merges 2 subtitle lines into 1
     - Uses first line's start time and second line's end time
     - Skips merging if combined text has >15 words (uses `_count_words()`)
     - Word counting uses regex `\b[\w-]+\b` to handle punctuation and hyphens
   - `convert_srt_to_ass()`: Converts to ASS format with separate styles for Chinese/English
     - **Chinese style**: Source Han Sans CN font, white text, dark reddish-brown outline (&H00503129), larger font, positioned below (MarginV=en_font_size+4)
     - **English style**: DejaVu Sans font, white text, black outline, smaller font, positioned at bottom (MarginV=0)
     - Separates Chinese and English lines into different Dialogue entries with Layer separation
   - `embed_subtitles_to_video()`: Hardcodes bilingual subtitles into video using FFmpeg
   - `generate_description_from_subtitle()`: Creates video description from translated subtitles
   - Translation prompts are stored in `prompts/translate.md` and `prompts/description.md`

9. **File Organization**:
   - Each video gets its own subfolder: `data/{author_name}|{video_id}/`
   - All files for a video (video, bilingual subtitles, descriptions, thumbnail) are stored in its subfolder
   - Example: `data/ChannelName|abc123/video.mp4`, `data/ChannelName|abc123/video_zh.srt`
   - Thumbnails are automatically downloaded and saved as `{video_title}.jpg`
   - **Subtitle files**: Only English subtitles `{title}.en.srt` are downloaded from YouTube
     - Bilingual subtitles `zh.srt` are generated by LLM translation (contains both English and Chinese)
     - Final embedded video: `{title}.mp4` (after subtitle embedding, original is `{title}_original.mp4`)
   - **Bilibili upload settings**: Videos are uploaded as reposts (转载)
     - `copyright=2`: Indicates repost content (not original)
     - `source`: YouTube original video URL
     - `repost_desc`: Repost declaration with channel name
     - Video descriptions no longer include YouTube URL at the beginning (it's in repost settings)
   - **Subscription monitoring**:
     - `youtuber.txt`: Channel list for subscription monitor (one per line)
       - Supports: `@username`, `UC...ID`, or full YouTube channel URLs
       - Empty lines and `#` comments are ignored
     - `subscription_history.json`: Persistent history of processed video IDs (in project root, not data/)
     - `.updating`: Lock file to prevent multiple monitor instances running simultaneously

10. **Author Batch Processing**: `scripts/author_videonum.txt` format is TSV: `channel_id\tmax_videos` (one per line, supports # comments)

11. **YouTube Download Format Handling** (`src/youtube/downloader.py`):
    - **1080p+ videos**: YouTube uses DASH format (separate video/audio streams) for higher resolutions
    - **Format selector priority**:
      1. Single-file mp4 at target resolution (480p/720p)
      2. Video + audio streams merged with FFmpeg (1080p+)
      3. Lower resolution fallback
      4. Any available format
    - Requires FFmpeg installed to merge video/audio streams for 1080p+

12. **Bilibili Content Optimization** (`src/bilibili/content_optimizer.py`):
    - **LLM-based Chinese title generation**: Automatically generates Chinese titles using LLM
      - Analyzes original English title and video description
      - Title length: 5-20 Chinese characters (max 80 chars)
      - Technical terms may remain in English (e.g., API, dlopen, Python)
      - Appends YouTuber name automatically: "中文标题 | YouTuber名"
      - Prompt stored in `prompts/generate_title.md`
      - Falls back to original title if LLM generation fails
    - **LLM-based tag generation**: Automatically generates 3-6 Chinese tags using LLM
      - Analyzes video description to extract relevant technical keywords
      - Tags limited to 5 Chinese characters, follows Bilibili user conventions
      - Falls back to YouTube tags and hot tag list if LLM generation fails
      - Prompt stored in `prompts/generate_tags.md`
    - Tag generation hierarchy:
      1. YouTuber name (if available)
      2. LLM-generated tags from video description
      3. YouTube original tags (translated to Chinese if needed)
      4. Hot tag matching (predefined CS-related tags)
      5. Language tags ("英语", "中文") for bilingual content
    - Maximum 12 tags per Bilibili upload (platform limit)

13. **Subscription Monitor Architecture** (`src/subscription_monitor.py`):
    - **Singleton pattern**: Uses file-based lock `.updating` to prevent concurrent executions
      - If lock file exists and process is running, new instance exits gracefully
      - Lock file automatically cleaned up on process exit (using `atexit`)
    - **History management**: Persistent JSON storage (`subscription_history.json` in project root)
      - Tracks all processed video IDs across runs
      - Survives process restarts and system reboots
      - Automatically backs up corrupted JSON files with `.json.corrupted` extension
    - **History updates**: When using `--full-workflow` (manually or via monitor)
      - History is updated automatically in `src/main.py` after successful upload
      - Both `subscription_monitor.py` and `main.py` use the same file path
      - Manual `--full-workflow` runs will also update history (preventing re-processing)
    - **Error recovery**: Corrupted history file is backed up and recreated from scratch
    - **Source of subscriptions**: Reads from `youtuber.txt` (one channel identifier per line)
      - Supports: `@username`, `UC...ID`, or full YouTube channel URLs
    - **Processing workflow**:
      1. Acquire singleton lock
      2. Fetch subscriptions from youtuber.txt
      3. For each channel, get latest N videos (default: 3)
      4. Filter out already-processed videos (from history)
      5. Process new videos serially using `--full-workflow`
      6. History is updated automatically by `run_full_workflow()` after successful upload
      7. Release lock on completion

## Code Quality Standards

**Ruff Configuration** (from `pyproject.toml`):
- Line length: 88 characters
- Target Python version: 3.13
- Enabled rule sets: E, F, W, I, N, B, C90
- Ignored: E501 (line length), B008 (function calls in defaults)

**Type Checking** (mypy):
- Python 3.13 target
- Strict mode: `disallow_untyped_defs = true`
- All new code should include type hints

**Testing Configuration** (pytest):
- Test files: `test_*.py` in `test/` directory
- Default options: `-v --tb=short`
- Uses pytest-asyncio for async test support

## Known Limitations

- YouTube download may require cookies to bypass bot detection (use `YOUTUBE_COOKIES_FILE` in .env)
- YouTube search restricted by anti-bot measures (API key recommended)
- Bilibili upload requires authentication cookies from browser
- Video embedding requires FFmpeg installed and available in PATH
- Subtitle translation requires OpenAI API key (or compatible endpoint) if YouTube auto-translate is unavailable
- mypy type checking is configured for Python 3.13 but project supports Python 3.9+

## Upload Optimization

When uploading to Bilibili, the system automatically:

1. **Uses Generated Description**: If `video_description.txt` exists in the video folder, it's used as the upload description (first line contains original YouTube URL)
2. **Finds Cover Image**: Searches for cover images in the video folder (supports .jpg, .jpeg, .png, .webp)
   - Prefers images with the same name as the video file
   - Falls back to any image file in the folder
3. **Fallback Behavior**: If no description file is found, uses a generated default description

## Utility Scripts

- **`src/utils/fix_you_srt_tl.py`**: Fixes subtitle timeline overlaps
  - Usage: `python src/utils/fix_you_srt_tl.py <file.srt> [FPS=60]`
  - Adjusts subtitle end times to prevent overlaps by using a 1-frame gap
  - Creates `file_fix.srt` alongside the original

## Unit Tests

The test suite covers critical subtitle processing functionality:

- **`test/test_subtitle_translation.py`**: Tests batch translation workflow
  - SRT file parsing
  - Batch formatting for LLM (`"1: Text\n2: Text\n..."`)
  - Translation result parsing and completeness validation
  - SRT rebuilding from translated text
  - Full workflow end-to-end test

- **`test/test_merge_algorithm.py`**: Tests smart subtitle merging
  - Word counting (`_count_words()`)
  - Merge logic with long combined text (>15 words stay separate)
  - Merge logic with short combined text (normal 2:1 merge)

- **`test/test_chinese_style.py`**: Tests ASS subtitle styling
  - Verifies `Chinese` style definition (Source Han Sans CN, white text, dark reddish-brown outline)
  - Confirms Chinese/English lines are separated into different Dialogues
  - Validates ASS file generation with correct styling

- **`test/test_video_processor.py`**: Tests video processing functionality
- **`test/test_youtube_searcher.py`**: Tests YouTube search and video filtering

## Common Workflow Patterns

When working with this codebase, you'll commonly encounter these patterns:

**1. Adding a New CLI Feature**:
- Add the argument to the `argparse` setup in `cli()` function ([`src/main.py`](src/main.py#L1691))
- Add a corresponding method to `YouTubeToBilibili` class
- Call the method from the `if __name__ == "__main__"` block with proper argument checks
- Update CLAUDE.md if the workflow is significant

**2. Extending Subtitle Processing**:
- All subtitle operations go through `SubtitleProcessor` class ([`src/core/subtitle_processor.py`](src/core/subtitle_processor.py))
- Follow the async/await pattern for I/O operations
- Use consistent SRT data structure: `{"index": int, "start": "HH:MM:SS,mmm", "end": "HH:MM:SS,mmm", "text": str}`
- For LLM operations, prompts are stored in `prompts/` directory
  - `translate.md`: Subtitle translation prompt (bilingual English+Chinese)
  - `description.md`: Video description generation prompt
  - `generate_tags.md`: Bilibili tag generation prompt
  - `generate_title.md`: Chinese title generation prompt

**3. File Naming Conventions**:
- Downloaded videos: `{title}.mp4` (original), `{title}_original.mp4` (before embedding)
- English subtitles from YouTube: `{title}.en.srt`
- Bilingual subtitles (LLM output): `zh.srt`
- Embedded video (final): `{title}.mp4`
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
