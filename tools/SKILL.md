# Clyde Tools Skill

**Skill Name:** clyde-tools  
**Description:** Orchestration skill for Clyde's tool ecosystem — video processing, graphics, browser control, presentations, and document generation.  
**Category:** software-development  
**Version:** 1.0.0  

## Triggers

Use when: Clyde needs to process media, generate graphics, control browser, or create presentations.  
One-line behavior: Loads the appropriate tool submodule (video, graphics, browser, presentations) based on the requested operation and executes the configured command.

## Directory Structure

```
~/Clyde/tools/
├── video/          — Video processing and generation
├── graphics/       — ASCII art, diagrams, design tools
├── browser/        — Browser automation and web interaction
├── presentations/  — Slide decks, documents, presentations
└── README.md       — This skill's overview
```

## Subskills (planned)

- `clyde-tools:video` — Video encoding, conversion, ASCII generation
- `clyde-tools:graphics` — ASCII art, SVG diagrams, design systems
- `clyde-tools:browser` — Browser control, scraping, automation
- `clyde-tools:presentations` — HTML/PowerPoint/ASCII slide generation

## Integration Points

- **Cron jobs:** Logs written to `~/Clyde/cron_logs/`
- **Training pipeline:** Tools available for post-training analysis and visualization
- **Hermes Agent:** Can invoke tool subskills via skill dispatch
- **Paperclip orchestration:** Tools integrate with Paperclip agent workflows

## Quick Commands (planned)

```bash
# Video
clyde video convert --input file.mp4 --output file.ascii.mp4
clyde video spectrogram --audio track.wav --output features.json

# Graphics
clyde graphics diagram --type architecture --output diagram.svg
clyde graphics infographic --layout 21 --style minimal --output infographic.png

# Browser
clyde browser navigate --url https://example.com --extract content
clyde browser fill-form --form login --submit

# Presentations
clyde presentations deck --style stripe --output deck.html
clyde presentations pptx --content slidedata.json --output slides.pptx
```

## Dependencies (planned)

- `ffmpeg` — video processing
- `manim-ce` — math animation generation
- `python-pptx` — PowerPoint creation/editing
- `beautifulsoup4` — web scraping
- `reportlab` — PDF generation
- `ascii-video` — ASCII video conversion (if available)

## Related Skills

- `hermes-agent` — Central coordination
- `clyde-training-workflow` — Training cycle management
- `paperclip-service-management` — Paperclip orchestration
- `gif-search` — GIF media operations
- `songsee` — Audio feature extraction
- `manim-video` — Math animation generation
- `popular-web-designs` — HTML/CSS design systems
- `claude-design` — HTML artifact creation
- `design-md` — DESIGN.md token spec files