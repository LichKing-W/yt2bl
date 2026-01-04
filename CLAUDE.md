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
- Bilingual subtitle embedding (English + Chinese) with ASS format support
- Video description generation from translated subtitles

## Architecture

```
src/
├── youtube/          # YouTube integration (search, download, models)
├── bilibili/         # Bilibili integration (upload, content optimization)
├── core/             # Video/subtitle processing (FFmpeg-based)
├── utils/            # Config, logging
└── main.py          # CLI entry point with YouTubeToBilibili class
```

**Key Patterns**:
- **Async/await**: All I/O operations use asyncio
- **Progressive enhancement**: Rich library is optional (fallback to plain text); YouTube API is optional (mock data fallback)
- **Modular design**: Each module (searcher, downloader, uploader) works independently

## Development Commands

**Setup**:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"  # Include dev dependencies
# Optional extras:
pip install -e ".[video]"    # For MoviePy video processing
pip install -e ".[bilibili]" # For Bilibili upload
pip install -e ".[translate]" # For subtitle translation via OpenAI
```

**Running**:
```bash
python -m src.main --max-videos 5
python -m src.main --url "https://youtube.com/watch?v=ID"
python -m src.main --channel-id "@username"  # Download from channel
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
1. Download video, English subtitles, and thumbnail to `data/{author}_{video_id}/`
2. Preprocess subtitles and translate them using LLM
3. Generate video description from translated subtitles (first line is original YouTube URL)
4. Create bilingual subtitles and embed into video
5. Upload to Bilibili with cover image and description

**Two-Step Workflow (Prepare + Upload)**:
```bash
# Step 1: Prepare (download, translate, embed) - stops before upload
python -m src.main --prepare "https://youtube.com/watch?v=VIDEO_ID"

# Step 2: Upload from prepared folder
python -m src.main --upload-folder "ChannelName_VIDEO_ID"
```
The `--prepare` command completes everything EXCEPT uploading to Bilibili:
- Downloads video, subtitles, and thumbnail to `data/{author}_{video_id}/`
- Translates subtitles to Chinese
- Merges and embeds bilingual subtitles into video
- Generates video description from translated subtitles
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
- `BILIBILI_SESSDATA`, `BILIBILI_BILI_JCT`, `BILIBILI_DedeUserID`: Required for upload
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`: For subtitle translation (default: gpt-4o-mini)
- `DOWNLOAD_PATH`: Default `./data`
- `MAX_VIDEO_SIZE_MB`, `VIDEO_QUALITY`, `UPLOAD_COOLDOWN_HOURS`, `AUTO_PUBLISH`

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
   - **Smart merge algorithm**: Skips merging if a line has >20 Chinese characters (uses `_count_chinese_characters()`)
   - **Chinese character detection**: Unicode range `\u4e00-\u9fff` for identifying Chinese text
   - `convert_srt_to_ass()`: Converts to ASS format with separate styles for Chinese/English
     - **Chinese style**: VYuan_Round font, white text, red outline, MarginV=60 (positioned above)
     - **English style**: Arial font, white text, blue outline, MarginV=30 (positioned below)
     - Separates Chinese and English lines into different Dialogue entries
   - `embed_subtitles_to_video()`: Hardcodes bilingual subtitles into video using FFmpeg
   - `generate_description_from_subtitle()`: Creates video description from translated subtitles
   - Translation prompts are stored in `prompts/translate.md` and `prompts/description.md`

9. **File Organization**:
   - Each video gets its own subfolder: `data/{author_name}_{video_id}/`
   - All files for a video (video, bilingual subtitles, descriptions, thumbnail) are stored in its subfolder
   - Example: `data/ChannelName_abc123/video.mp4`, `data/ChannelName_abc123/video_zh.srt`
   - Thumbnails are automatically downloaded and saved as `{video_title}.jpg`
   - **Subtitle files**: Only English subtitles `{title}.en.srt` are downloaded from YouTube
     - Bilingual subtitles `zh.srt` are generated by LLM translation (contains both English and Chinese)
     - Final embedded video: `{title}.mp4` (after subtitle embedding, original is `{title}_original.mp4`)
   - **Bilibili upload settings**: Videos are uploaded as reposts (转载)
     - `copyright=2`: Indicates repost content (not original)
     - `source`: YouTube original video URL
     - `repost_desc`: Repost declaration with channel name
     - Video descriptions no longer include YouTube URL at the beginning (it's in repost settings)

10. **Author Batch Processing**: `scripts/author_videonum.txt` format is TSV: `channel_id\tmax_videos` (one per line, supports # comments)

11. **YouTube Download Format Handling** (`src/youtube/downloader.py`):
    - **1080p+ videos**: YouTube uses DASH format (separate video/audio streams) for higher resolutions
    - **Format selector priority**:
      1. Single-file mp4 at target resolution (480p/720p)
      2. Video + audio streams merged with FFmpeg (1080p+)
      3. Lower resolution fallback
      4. Any available format
    - Requires FFmpeg installed to merge video/audio streams for 1080p+

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
  - Chinese character counting (`_count_chinese_characters()`)
  - Merge logic with long Chinese lines (>20 chars stay separate)
  - Merge logic with short Chinese lines (normal 2:1 merge)

- **`test/test_chinese_style.py`**: Tests ASS subtitle styling
  - Verifies `Chinese` style definition (VYuan_Round, white text, blue outline)
  - Confirms Chinese/English lines are separated into different Dialogues
  - Validates ASS file generation with correct styling

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
