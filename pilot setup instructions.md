Here's the Project Hermes Backend Pilot formatted in Markdown:

---

# Backend Pilot for Project Hermes

You're building the backend for **Project Hermes**, a lightweight news digest tool that filters out noise and summarizes high-signal stories.

🎯 **GOAL:**
Build a minimal working Python backend script that:
1.  Scrapes or pulls top news headlines from free sources.
2.  Filters out unwanted topics (e.g., local crime, celebrity gossip).
3.  Summarizes 5–10 selected articles using GPT-4 or OpenAI API.
4.  Outputs a clean, structured daily digest in Markdown format.

📁 **Folder structure:**

```
project_hermes/
├── main.py
├── news_fetcher.py
├── filter_engine.py
├── summarizer.py
├── digest_writer.py
├── config.py
└── data/
└── digests/
```

🧱 **Modules:**

1.  **`news_fetcher.py`**
    *   Use `feedparser` or `newspaper3k` to fetch articles from at least 3 reliable sources (e.g., Reuters, BBC, AP).
    *   Extract title, summary, link, and article text.

2.  **`filter_engine.py`**
    *   Apply keyword filtering to exclude sensational/local news (e.g., “shooting,” “celebrity,” “arrested”).
    *   Include topics like tech, climate, geopolitics, science, economy.
    *   Use basic keyword logic for now.

3.  **`summarizer.py`**
    *   Use OpenAI’s GPT API to summarize each article into 3–5 bullet points.
    *   Add a category tag (e.g., `[Tech]`, `[Climate]`) inferred from content.

4.  **`digest_writer.py`**
    *   Group summaries into sections.
    *   Output clean Markdown file titled with today’s date.
    *   Include: title, summary bullets, source link.

5.  **`main.py`**
    *   Orchestrates everything: fetch → filter → summarize → write.
    *   Can be scheduled via CRON or run manually.

6.  **`config.py`**
    *   Contains all API keys, topic filters, and constants.

🧪 Start with a prototype that works end-to-end with 3–5 stories and only 3 sources. Prioritize clean output, reliable parsing, and safe API calls.

📥 **Output example:**

```markdown
# 🗞️ Project Hermes Digest — August 7, 2025

## 🌍 Global Affairs
**Ukraine and Russia Tensions Escalate Over Black Sea**
- Russia increased naval patrols near Odessa.
- Ukraine responded with aerial surveillance and NATO consultation.
- Ongoing threat to grain exports from the region.
[Read more →](https://www.reuters.com/...)

## ⚙️ Tech & AI
**AI Beats Radiologists in Early Cancer Detection**
- New study finds GPT-4-like model outperforms experts.
- Accuracy improves early-stage identification by 17%.
[Read more →](https://www.bbc.com/...)
```

🧠 **Limitations to handle later:**

*   Advanced semantic filtering
*   UI frontend
*   Long-term thread memory

Keep code modular and readable — this will serve as the seed for scaling into a full tool.