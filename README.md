# 🗞️ Hermes

*A signal filter for noise-free news digests*

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Project Hermes is a lightweight, AI-powered tool that curates high-signal, low-noise news digests. It cuts through sensationalist headlines and emotional manipulation to surface what truly matters — from geopolitics to breakthrough science.

## ✨ Vision

Transform the overwhelming noise of daily news into structured, meaningful updates that deliver clarity, context, and calm in our distracted digital age. Hermes isn't another news app — it's your personal analyst for civilizational awareness.

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/BenWassa/Hermes.git
cd Hermes

# Install the package
pip install -e .

# Optional: Install with AI features
pip install -e ".[ai]"

# Set up OpenAI API key (if using AI summarization)
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

## 🏗️ Project Structure

```
hermes/
├── hermes/                 # Main package
│   ├── __init__.py
│   ├── cli.py             # Command-line interface
│   ├── config.py          # Configuration and constants
│   ├── fetcher.py         # RSS feed parsing and article extraction
│   ├── filter.py          # Content filtering and categorization
│   ├── main.py            # Pipeline orchestration
│   ├── summarizer.py      # AI-powered summarization
│   └── writer.py          # Multi-format digest generation
├── tests/                 # Test suite
├── data/                  # Output and cache directory
│   └── digests/           # Generated digest files
├── docs/                  # Documentation
├── pyproject.toml         # Project configuration
└── requirements.txt       # Dependencies
```

## 🛠️ Technology Stack

| Layer | Current Implementation | Future Upgrades |
|-------|----------------------|------------------|
| **Scraping** | feedparser, newspaper3k | News API, Google News API |
| **Filtering** | Keyword logic, regex | spaCy, transformers, LangChain |
| **Summarization** | OpenAI GPT-4o-mini | Claude, Gemini, fine-tuned models |
| **CLI** | Built-in Python interface | Web UI, mobile app |
| **Storage** | Local files (MD/JSON) | SQLite, Notion API, Supabase |

## 📊 Content Categories

Hermes organizes news into focused categories:

- **🌍 Global Affairs** — Politics, diplomacy, international relations
- **⚙️ Tech & AI** — Technology breakthroughs, AI developments, digital trends  
- **🧬 Science & Health** — Research discoveries, medical advances, climate science
- **📊 Economy & Policy** — Markets, regulations, economic analysis
- **📚 Culture & Ideas** — Society, education, philosophical developments

## 🚀 Roadmap

| Phase | Milestone | Description |
|-------|-----------|-------------|
| **1** | Lean Prototype ✅ | Local script outputting clean Markdown digests |
| **2** | Web Interface | Flask/React frontend for browsing and searching |
| **3** | Integrations | Auto-publish to Notion, email, RSS |
| **4** | Analytics | Visualize story trends and attention patterns |
| **5** | Audio Mode | TTS-powered audio digest podcasts |
| **6** | Knowledge Graph | Contextual story threading over time |

## 🤝 Contributing

Hermes is designed to be modular and extensible. Contributions are welcome!

### Development Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black hermes/

# Type checking
mypy hermes/
```

### Areas for Contribution

- **Enhanced filtering algorithms** using semantic analysis
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
**Project**: [github.com/BenWassa/Hermes](https://github.com/BenWassa/Hermes)
