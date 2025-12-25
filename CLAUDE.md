# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube to Bilibili video transfer tool for computer science content. The project searches YouTube for CS-related videos, downloads them, processes/format-converts them, and uploads to Bilibili with content localization (Chinese titles, descriptions, tags).

**Tech Stack**: Python 3.9+ (3.13 preferred), UV package manager, yt-dlp, bilibili-api-python, asyncio, Rich CLI, Pydantic.

## Architecture

```
src/
├── youtube/          # YouTube integration (search, download, models)
├── bilibili/         # Bilibili integration (upload, content optimization)
├── core/             # Video/subtitle processing (MoviePy/FFmpeg)
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
./setup.sh              # Quick setup (venv + install)
# Or manually:
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"  # Include dev dependencies
```

**Running**:
```bash
python -m src.main --max-videos 5
python -m src.main --url "https://youtube.com/watch?v=ID"
yt2bl --max-videos 3    # After pip install -e .
./scripts/run_dev.sh    # Dev mode script
```

**Testing**:
```bash
pytest test/ -v                    # Run all tests
pytest test/test_specific.py -v    # Single test file
./scripts/quick_test.sh            # Quick test script
./scripts/test_minimal.sh          # Minimal test
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
- `BILIBILI_SESSDATA`, `BILIBILI_BILI_JCT`, `BILIBILI_DedeUserID`: Required for upload
- `DOWNLOAD_PATH`: Default `./data`
- `MAX_VIDEO_SIZE_MB`, `VIDEO_QUALITY`, `UPLOAD_COOLDOWN_HOURS`, `AUTO_PUBLISH`

## Important Implementation Details

1. **CS Content Filtering**: `src/youtube/models.py` contains 87+ computer science keywords for content filtering in `YouTubeVideo.is_cs_content()`

2. **Quality Scoring**: `YouTubeVideo.get_quality_score()` rates videos based on views, engagement, duration

3. **Progress Tracking**: Download operations accept an `update_progress(percent, speed)` callback for Rich progress bars

4. **Error Handling**: Extensive try-catch with graceful degradation. Check `src/main.py` for patterns (RICH_AVAILABLE flag for optional Rich library)

5. **Video Processing**: `src/core/video_processor.py` uses MoviePy (optional dependency - install with `pip install -e ".[video]"`)

## Known Limitations

- YouTube search restricted by anti-bot measures (API key recommended)
- Bilibili upload requires authentication cookies from browser
- Video format conversion integration is partial/in progress
