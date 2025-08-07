# 🗞️ Hermes

*A signal filter for noise-free news digests*

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: ## 🤝 Contributing

Hermes is designed to be modular and extensible. Contributions are welcome!

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install -e .

# Run tests
pytest

# Format code
black hermes/
```

### Areas for Contribution

- **Improved filtering algorithms** using semantic analysis
- **Additional news sources** and feed parsers
- **Frontend interface** for digest browsing and interaction
- **Integration plugins** for Notion, email, RSS output
- **Performance optimizations** and caching strategies

## 🧠 Philosophy & Future Vision

> *"Hermes – Messenger of the gods, psychopomp, god of communication, boundaries, and trade. Perfect for a system that travels between chaos and clarity, synthesizing messages for human understanding."*

### Open Questions

As Hermes evolves, we're exploring deeper questions about information consumption:

- **Personalization**: Should Hermes learn your reading preferences?
- **Interrogation**: Can you ask "What's the latest on climate policy in Europe?"  
- **Perspective**: Should it offer the same story from multiple viewpoints?
- **Memory**: How do we track evolving narratives over time?

These are ethical, technical, and philosophical challenges that will shape future development.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Built with gratitude for the open-source ecosystem and the journalists who risk their lives to bring us truth.

---

**Last updated**: August 7, 2025  
**Author**: [Benjamin P. Haddon](https://github.com/BenWassa)  
**Project**: [github.com/BenWassa/Hermes](https://github.com/BenWassa/Hermes)shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Project Hermes is a lightweight, AI-powered tool that curates high-signal, low-noise news digests. It cuts through sensationalist headlines and emotional manipulation to surface what truly matters — from geopolitics to breakthrough science.

## ✨ Vision

Transform the overwhelming noise of daily news into structured, meaningful updates that deliver clarity, context, and calm in our distracted digital age. Hermes isn't another news app — it's your personal analyst for civilizational awareness.A living signal filter and cultural observatory that curates clarity from the world’s noise. Hermes tracks civilizational shifts through daily summaries, transforming global news into a ritual of awareness — minimalist, mobile, and meaning-driven.

Project Hermes
A lean, intelligent news digest that cuts through the noise.

📌 Vision
Project Hermes is a lightweight, customizable, and AI-powered tool that curates high-signal, low-noise news recaps. It aims to replace sensationalist feeds with structured, meaningful updates — delivering clarity, context, and calm in a distracted digital age.

Hermes isn't another news app — it's your personal analyst, filtering out emotional manipulation and surfacing what truly matters, from geopolitics to breakthrough science.

## � Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/BenWassa/Hermes.git
cd Hermes

# Install dependencies
pip install -r requirements.txt

# Optional: Set up OpenAI API for advanced summarization
export OPENAI_API_KEY="your-api-key-here"
```

### Usage

```bash
# Generate today's digest
python -m hermes.main

# Specify output format
python -m hermes.main --format html

# Enable verbose logging
python -m hermes.main --verbose
```

### Example Output

```markdown
# 🗞️ Hermes Daily Digest — 2025-08-07

## 🌍 Global Affairs
### Climate Summit Reaches Historic Agreement
- 50+ nations commit to net-zero emissions by 2040
- Breakthrough financing mechanism for developing countries
- Technology transfer agreements accelerate green transition

[Read full article →](https://example.com/...)
```

## 💡 Core Philosophy

- **🧠 Signal over noise** — Filter out reactive reporting and highlight systemic, civilization-level developments
- **🛠️ Minimalist & modular** — Lean architecture that adapts to different formats and use cases  
- **🧘‍♂️ Cognitive clarity** — Neutral, grounded tone that reduces fatigue while enhancing understanding
- **🧵 Narrative cohesion** — Prioritize ongoing stories and slow developments over headline churn

## 🏗️ Architecture

```
hermes/
├── config.py          # Configuration and constants
├── fetcher.py         # RSS feed parsing and article extraction  
├── filter.py          # Content filtering and categorization
├── summarizer.py      # AI-powered summarization
├── writer.py          # Multi-format digest generation
└── main.py            # Pipeline orchestration
```

### Core Components

| Component | Description |
|-----------|-------------|
| **Fetcher** | Pulls articles from RSS feeds (Reuters, BBC, AP News) |
| **Filter** | Removes noise using keyword rules and semantic scoring |
| **Summarizer** | Generates bullet-point summaries using OpenAI or fallback methods |
| **Writer** | Outputs clean digests in Markdown, HTML, or JSON |
| **Scheduler** | (Planned) Automates daily runs via CRON or GitHub Actions |

## 🛠️ Technology Stack

| Layer | Current Implementation | Future Upgrades |
|-------|----------------------|------------------|
| **Scraping** | feedparser, newspaper3k | News API, Google News API |
| **Filtering** | Keyword logic, regex | spaCy, transformers, LangChain |
| **Summarization** | OpenAI GPT-4o-mini | Claude, Gemini, fine-tuned models |
| **Scheduling** | Manual execution | GitHub Actions, CRON, Prefect |
| **Frontend** | Static file output | Flask webapp, React PWA |
| **Storage** | Local files (MD/JSON) | SQLite, Notion API, Supabase |

## 📊 Content Categories

Hermes organizes news into focused categories:

- **🌍 Global Affairs** — Politics, diplomacy, international relations
- **⚙️ Tech & AI** — Technology breakthroughs, AI developments, digital trends  
- **🧬 Science & Health** — Research discoveries, medical advances, climate science
- **📊 Economy & Policy** — Markets, regulations, economic analysis
- **📚 Culture & Ideas** — Society, education, philosophical developments

🧪 Limitations
Area	Limitation	Proposed Solution
API Limits	News APIs often rate-limit or gatekeep premium content	Use multiple sources, rotate, or fall back to RSS
Model Latency	GPT/Claude calls can be slow or costly at scale	Cache summaries, prioritize high-impact stories
Sensational Filtering	Nuanced distinction between “impact” and “emotion-bait”	Use rules + LLM scoring to calibrate
Freshness	Delay between scraping and posting	Optimize fetch time, consider push-based updates
Visual Noise	News websites are full of ads/images	Use text-only parsing (e.g., newspaper3k)

🔍 Content Rules (Signal Filtering)
Filter Type	Rule Example
Location Noise	Exclude articles with local-only context (e.g., "Toronto man arrested...")
Topic Priority	Include: geopolitics, climate, tech, science, economy
Sentiment Check	Discard content with high emotional polarity unless structurally relevant
Source Whitelist	Prioritize sources like Reuters, AP, ScienceDirect, Nature, Foreign Affairs
Temporal Threads	Flag ongoing stories (e.g., election cycles, war, economic downturns)

🗂 Output Formats
HTML: Responsive digest for personal reading or newsletter

Markdown: Plain text version for version control or archiving

JSON: Structured summaries for API or integration

Notion (optional): Push directly to a daily page for reading

Audio? (stretch goal): Use TTS to generate daily audio news brief

🔄 Daily Workflow (Prototype Phase)
Morning Fetch (6:00 AM)

Pull top 50 articles across 5–10 sources

Filtering

Apply topic and quality filters

Summarization

Generate short-form summary with context tags (e.g., [Climate], [Policy], [AI])

Digest Creation

Organize into 3–5 section categories:

🌍 Global Affairs

⚙️ Tech & AI

🧬 Science & Health

📊 Economy & Policy

📚 Culture & Ideas

Publish or Archive

Output to folder or push to Notion, webapp, etc.

🚀 Expansion Roadmap
Phase	Milestone	Description
1	Lean Prototype	Run a local script that outputs clean Markdown digest from news feeds
2	Structured Output + UI	Build small frontend (e.g., Flask) to view past digests, search, filter
3	Notion/Email Push	Auto-publish summaries to Notion or email daily
4	Interactive Heatmap	Visualize story weight or attention over time (Hermes + Project Iris?)
5	Voice Mode	Read summaries aloud using TTS as audio podcast
6	Knowledge Graph Backend	Tag stories by evolving threads and structure contextually over time

📘 Naming Notes
Hermes – Messenger of the gods, psychopomp, god of communication, boundaries, and trade. Perfect for a system that travels between chaos and clarity, synthesizing messages for human understanding.

🧠 Meta Considerations
Should Hermes remember you? E.g., remember your preferred story categories?

Should it let you ask questions like: “What’s the latest on the climate lawsuit in Montana?”

Should it learn what you skip or read deeply?

Should it allow “perspective mode” — same story from Left, Center, and Right?

These are ethical, technical, and philosophical questions for later iterations.


Last updated: Aug 7, 2025
Author: [Benjamin P. Haddon](https://github.com/BenWassa)
