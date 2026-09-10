"""Compact Hermes destinations for Core Voice release alerts.

The release watcher owns *discovery and claiming*.  This module starts only
after that claim is durable.  It turns one already-qualified article into a
small, stable static page and the restrained ntfy alert that points at it.

No article body is fetched here.  The summarizer sees only the public metadata
already returned by the configured Voice adapters (headline, publication,
publication date, and publisher/feed descriptions).  This keeps access-control
boundaries unchanged and makes model/request cost proportional to actual alerts,
not candidates or hourly watcher passes.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from .. import config
from .model import VoiceArticle
from .names import clean_text
from .notify import Alert, voice_names

log = logging.getLogger("the-daily.voices.release")
UTC = dt.timezone.utc
TORONTO = ZoneInfo(config.TIMEZONE)

ARTICLE_ROOT = Path("docs/voices/articles")
MAX_SOURCE_CHARS = 7000
MAX_DESCRIPTION_CHARS = 3500
MAX_THESIS_CHARS = 700
MAX_TAKEAWAY_CHARS = 360
MAX_WHY_CHARS = 420
MAX_ALERT_TAKEAWAY_CHARS = 220
SUMMARY_MAX_TOKENS = int(os.environ.get("VOICE_RELEASE_SUMMARY_MAX_TOKENS", "1600"))
SUMMARY_THINKING_BUDGET = int(os.environ.get("VOICE_RELEASE_SUMMARY_THINKING_BUDGET", "256"))
_FALLBACK_MODEL = "gemini-2.5-flash"
_RETRY_CODES = {429, 500, 503}


@dataclass(frozen=True)
class ReleaseSummary:
    thesis: str
    takeaways: tuple[str, ...] = ()
    why_it_matters: str = ""
    limitation: str = ""

    @property
    def alert_takeaway(self) -> str:
        text = self.takeaways[0] if self.takeaways else self.thesis
        return _clip(text, MAX_ALERT_TAKEAWAY_CHARS)


@dataclass(frozen=True)
class PreparedRelease:
    alert: Alert
    page_published: bool
    model_used: bool
    summary_fallback: bool
    fallback_reason: str = ""


class SummaryProvider:
    def summarize(self, article: VoiceArticle, *, writers: str) -> ReleaseSummary:
        raise NotImplementedError


class PagePublisher:
    def publish(self, path: Path, page_html: str, message: str) -> bool:
        raise NotImplementedError


def _clip(value: object, limit: int) -> str:
    text = clean_text(str(value or ""))
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


def original_url(article: VoiceArticle) -> str:
    """Use the source-stated publisher URL for navigation.

    Hermes's canonical URL is deliberately normalized for identity matching and
    can remove addressing details such as ``www.``.  The source-stated URL is
    therefore the safest reader destination, while canonical identity remains
    the dedupe authority.
    """
    return article.url or article.canonical_url


def article_token(article: VoiceArticle) -> str:
    """Opaque deterministic path component; no headline or publisher leaks into paths."""
    return hashlib.sha256(article.key.encode("utf-8")).hexdigest()[:24]


def article_page_path(article: VoiceArticle) -> Path:
    return ARTICLE_ROOT / article_token(article) / "index.html"


def article_page_url(article: VoiceArticle) -> str:
    base = config.SITE_URL.rstrip("/") + "/"
    return urljoin(base, f"voices/articles/{article_token(article)}/")


def source_material(article: VoiceArticle) -> tuple[str, bool]:
    """Return de-duplicated legitimately supplied descriptions and whether they are rich enough.

    This function never follows the article URL and never attempts to obtain a
    body.  Descriptions are already-public adapter metadata.  The boolean is a
    conservative model gate: a headline alone does not justify asking a model
    to invent the article's argument.
    """
    descriptions: list[str] = []
    for value in [article.description, *(obs.description for obs in article.observations)]:
        text = _clip(value, MAX_DESCRIPTION_CHARS)
        if text and text not in descriptions:
            descriptions.append(text)

    material = "\n\n".join(descriptions)
    material = material[:MAX_SOURCE_CHARS].rstrip()
    # A short deck/trail can support a deterministic metadata fallback, but a
    # model should receive enough substance to do more than paraphrase a title.
    return material, len(material) >= 120


def metadata_summary(article: VoiceArticle, *, writers: str, reason: str = "") -> ReleaseSummary:
    material, _ = source_material(article)
    if material:
        thesis = _clip(material, MAX_THESIS_CHARS)
        limitation = (
            "Hermes is summarizing from publisher-provided description metadata; "
            "full article text was not available to this alert path."
        )
    else:
        thesis = (
            f"Hermes confirmed this new piece by {writers or 'a Core Voice'}, but the "
            "available source metadata does not contain enough detail to summarize "
            "its argument reliably."
        )
        limitation = (
            "Only headline, authorship, publication and link metadata were available."
        )
    if reason:
        limitation = f"{limitation} {reason}"
    return ReleaseSummary(thesis=thesis, limitation=limitation)


class MetadataSummaryProvider(SummaryProvider):
    """No-model provider used by dry runs and as an explicit conservative fallback."""

    def summarize(self, article: VoiceArticle, *, writers: str) -> ReleaseSummary:
        return metadata_summary(article, writers=writers)


class GeminiSummaryProvider(SummaryProvider):
    """One logical Gemini summary generation for one already-claimed alert."""

    def __init__(self, *, client=None, model: str | None = None, retries: int = 2):
        self.client = client
        self.model = model or config.CURATE_MODEL
        self.retries = retries

    def _client(self):
        if self.client is not None:
            return self.client
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) not set")
        self.client = genai.Client(api_key=key)
        return self.client

    def _config(self, model: str) -> types.GenerateContentConfig:
        kwargs: dict = {
            "system_instruction": (
                "You summarize one opinion/essay article for a private finite newspaper. "
                "Use only the supplied public metadata. Attribute arguments to the writer, "
                "never to Hermes. Do not infer facts or arguments not supported by the input. "
                "Return concise JSON only. Do not quote long source passages."
            ),
            "response_mime_type": "application/json",
            "max_output_tokens": SUMMARY_MAX_TOKENS,
            "temperature": 0.2,
        }
        if "2.5" in model:
            kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_budget=SUMMARY_THINKING_BUDGET
            )
        return types.GenerateContentConfig(**kwargs)

    def _generate(self, payload: str):
        client = self._client()
        models = [self.model]
        if self.model != _FALLBACK_MODEL:
            models.append(_FALLBACK_MODEL)
        last: Exception | None = None
        for model in models:
            cfg = self._config(model)
            for attempt in range(self.retries + 1):
                try:
                    return client.models.generate_content(
                        model=model, contents=payload, config=cfg
                    )
                except genai_errors.APIError as exc:
                    last = exc
                    code = getattr(exc, "code", None)
                    if code in _RETRY_CODES and attempt < self.retries:
                        time.sleep(min(20, 2 * (2**attempt)))
                        continue
                    break
        if last is not None:
            raise last
        raise RuntimeError("Gemini summary generation failed")

    def summarize(self, article: VoiceArticle, *, writers: str) -> ReleaseSummary:
        material, rich_enough = source_material(article)
        if not rich_enough:
            return metadata_summary(article, writers=writers)

        payload = json.dumps(
            {
                "writer": writers,
                "publication": article.publication,
                "publication_date": (
                    article.published_at.astimezone(UTC).isoformat()
                    if article.published_at
                    else None
                ),
                "headline": article.title,
                "paywalled": article.paywalled,
                "available_public_description_material": material,
                "output": {
                    "thesis": "1-2 concise sentences",
                    "takeaways": "0-5 short arguments/takeaways, only when supported",
                    "why_it_matters": "optional short string, or empty",
                },
            },
            ensure_ascii=False,
        )
        response = self._generate(payload)
        if not response.text:
            raise RuntimeError("empty Gemini release summary")
        raw = json.loads(response.text)
        if not isinstance(raw, dict):
            raise ValueError("release summary response must be an object")

        thesis = _clip(raw.get("thesis"), MAX_THESIS_CHARS)
        if not thesis:
            raise ValueError("release summary omitted thesis")
        takeaways_raw = raw.get("takeaways") or []
        if not isinstance(takeaways_raw, list):
            takeaways_raw = []
        takeaways = tuple(
            text
            for text in (_clip(item, MAX_TAKEAWAY_CHARS) for item in takeaways_raw[:5])
            if text
        )
        why = _clip(raw.get("why_it_matters"), MAX_WHY_CHARS)
        limitation = ""
        if article.paywalled:
            limitation = (
                "Summary is based on legitimately accessible publisher metadata; "
                "Hermes did not bypass subscriber access controls."
            )
        return ReleaseSummary(
            thesis=thesis,
            takeaways=takeaways,
            why_it_matters=why,
            limitation=limitation,
        )


def _format_date(value: dt.datetime | None) -> str:
    if value is None:
        return "Publication date unavailable"
    local = value.astimezone(TORONTO)
    return f"{local.strftime('%B')} {local.day}, {local.year}"


def render_release_page(
    article: VoiceArticle,
    *,
    writers: str,
    summary: ReleaseSummary,
) -> str:
    """Render one self-contained stable summary page, never an article feed."""
    original = original_url(article)
    if not original.startswith(("http://", "https://")):
        raise ValueError("release page requires an absolute publisher URL")

    publication = clean_text(article.publication) or "Original publication"
    date_label = _format_date(article.published_at)
    takeaways_html = ""
    if summary.takeaways:
        items = "".join(f"<li>{html.escape(item)}</li>" for item in summary.takeaways[:5])
        takeaways_html = (
            '<section class="section" aria-labelledby="takeaways">'
            '<h2 id="takeaways">Key takeaways</h2>'
            f"<ul>{items}</ul></section>"
        )
    why_html = ""
    if summary.why_it_matters:
        why_html = (
            '<section class="section" aria-labelledby="why">'
            '<h2 id="why">Why it matters</h2>'
            f"<p>{html.escape(summary.why_it_matters)}</p></section>"
        )
    limitation_html = ""
    if summary.limitation:
        limitation_html = (
            f'<p class="limitation">{html.escape(summary.limitation)}</p>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="robots" content="noindex,follow" />
  <meta name="theme-color" content="#1a2744" media="(prefers-color-scheme: light)" />
  <meta name="theme-color" content="#101722" media="(prefers-color-scheme: dark)" />
  <title>{html.escape(article.title)} · The Daily</title>
  <style>
    :root {{
      --paper:#faf8f3; --desk:#efece6; --ink:#17130d; --meta:#6c665c;
      --rule:#dcd6cc; --navy:#1a2744; --link:#1a2744; --note:#f2eee6;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --paper:#151a22; --desk:#0e1219; --ink:#e9e3d5; --meta:#a39c8f;
        --rule:#2f3540; --navy:#a3b3d2; --link:#b7c5df; --note:#1d232d;
      }}
    }}
    * {{ box-sizing:border-box; }}
    html,body {{ margin:0; background:var(--desk); }}
    body {{ color:var(--ink); font-family:Georgia,serif; -webkit-font-smoothing:antialiased; }}
    main {{
      min-height:100vh; min-height:100svh; max-width:720px; margin:0 auto;
      background:var(--paper);
      padding:calc(20px + env(safe-area-inset-top)) calc(20px + env(safe-area-inset-right))
              calc(42px + env(safe-area-inset-bottom)) calc(20px + env(safe-area-inset-left));
    }}
    .brand {{
      font-family:Arial,sans-serif; color:var(--navy); text-decoration:none;
      font-size:.72rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
      display:inline-flex; align-items:center; min-height:44px;
    }}
    header {{ border-top:4px solid var(--navy); padding:18px 0 22px; border-bottom:1px solid var(--rule); }}
    .eyebrow {{
      font-family:Arial,sans-serif; color:var(--meta); font-size:.68rem; font-weight:700;
      letter-spacing:.13em; text-transform:uppercase; margin-bottom:8px;
    }}
    h1 {{ font-size:clamp(2rem,8vw,3rem); line-height:1.02; margin:0 0 14px; color:var(--navy); overflow-wrap:anywhere; }}
    .meta {{ font-family:Arial,sans-serif; color:var(--meta); font-size:.78rem; line-height:1.55; }}
    .thesis {{ font-size:1.16rem; line-height:1.58; margin:24px 0 4px; }}
    .section {{ border-top:1px solid var(--rule); padding:21px 0 2px; margin-top:22px; }}
    h2 {{ font-size:1rem; line-height:1.2; margin:0 0 10px; color:var(--navy); }}
    p {{ line-height:1.58; }}
    ul {{ margin:0; padding-left:1.25rem; }}
    li {{ line-height:1.52; margin:0 0 10px; padding-left:.15rem; }}
    .limitation {{
      background:var(--note); color:var(--meta); font-family:Arial,sans-serif;
      font-size:.74rem; line-height:1.5; padding:12px 14px; margin:22px 0 0;
    }}
    .original {{
      border-top:1px solid var(--rule); margin-top:26px; padding-top:18px;
      display:flex; flex-wrap:wrap; align-items:center; gap:12px;
    }}
    .read {{
      color:var(--paper); background:var(--navy); font-family:Arial,sans-serif;
      font-size:.8rem; font-weight:700; text-decoration:none; display:inline-flex;
      align-items:center; justify-content:center; min-height:48px; padding:0 17px;
    }}
    .source {{ font-family:Arial,sans-serif; color:var(--meta); font-size:.72rem; line-height:1.4; }}
    .read:focus-visible,.brand:focus-visible {{ outline:2px solid var(--link); outline-offset:3px; }}
    @media (prefers-color-scheme:dark) {{ .read {{ color:#101722; }} }}
  </style>
</head>
<body>
  <main>
    <a class="brand" href="../../../">The Daily</a>
    <header>
      <div class="eyebrow">Core Voice · Article summary</div>
      <h1>{html.escape(article.title)}</h1>
      <div class="meta">{html.escape(writers)} · {html.escape(publication)} · {html.escape(date_label)}</div>
    </header>
    <article aria-label="Hermes summary of the original article">
      <p class="thesis">{html.escape(summary.thesis)}</p>
      {takeaways_html}
      {why_html}
      {limitation_html}
      <div class="original">
        <a class="read" href="{html.escape(original, quote=True)}" target="_blank" rel="noopener">Read original <span aria-hidden="true">→</span></a>
        <span class="source">Opens {html.escape(publication)}</span>
      </div>
    </article>
  </main>
</body>
</html>
"""


def build_release_alert(
    article: VoiceArticle,
    *,
    writers: str,
    summary: ReleaseSummary,
    click: str,
) -> Alert:
    headline = _clip(article.title, 180)
    title = " — ".join(part for part in (writers, headline) if part) or "Core Voice"
    takeaway = summary.alert_takeaway or "A new Core Voice article is available."
    return Alert(title=title, message=takeaway, click=click, article_key=article.key)


class FileArticlePagePublisher(PagePublisher):
    def publish(self, path: Path, page_html: str, message: str) -> bool:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page_html, encoding="utf-8")
        return True


class DryRunArticlePagePublisher(PagePublisher):
    """Pretend publication succeeded while writing nothing."""

    def publish(self, path: Path, page_html: str, message: str) -> bool:
        return True


class GitArticlePageError(RuntimeError):
    pass


class GitArticlePagePublisher(PagePublisher):
    """Publish one immutable article page with bounded git push retries.

    The watcher's claim has already been pushed before this class is called.
    A rejected page push therefore resets to the newest branch, rewrites only
    this content-addressed page, and retries.  It never edits watcher state.
    """

    def __init__(
        self,
        *,
        repo: Path | str = ".",
        branch: str = "main",
        remote: str = "origin",
        attempts: int | None = None,
        author_name: str = "github-actions[bot]",
        author_email: str = "github-actions[bot]@users.noreply.github.com",
    ):
        self.repo = Path(repo)
        self.branch = branch
        self.remote = remote
        self.attempts = attempts or config.VOICE_WATCH_PUSH_ATTEMPTS
        self.author_name = author_name
        self.author_email = author_email

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["git", *args], cwd=str(self.repo), capture_output=True, text=True, check=False
        )
        if check and result.returncode != 0:
            raise GitArticlePageError(
                f"git {' '.join(args)} failed ({result.returncode}): "
                f"{(result.stderr or result.stdout).strip()}"
            )
        return result

    def _relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.repo.resolve()).as_posix()
        except ValueError as exc:
            raise GitArticlePageError("article page must be inside the repository") from exc

    def publish(self, path: Path, page_html: str, message: str) -> bool:
        rel = self._relative(path)
        root = ARTICLE_ROOT.as_posix().rstrip("/") + "/"
        if not rel.startswith(root) or not rel.endswith("/index.html"):
            raise GitArticlePageError(f"refusing unexpected article page path: {rel}")

        for attempt in range(1, self.attempts + 1):
            if attempt > 1:
                self._git("fetch", self.remote, self.branch)
                self._git("reset", "--hard", f"{self.remote}/{self.branch}")
                self._git("clean", "--force", "--", rel, check=False)

            status = self._git("status", "--porcelain", "--untracked-files=all").stdout.splitlines()
            stray = [line for line in status if line[3:].strip().strip('"') != rel]
            if stray:
                raise GitArticlePageError(
                    "refusing to publish article page with unrelated working-tree changes: "
                    + ", ".join(line[3:] for line in stray[:5])
                )

            target = self.repo / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page_html, encoding="utf-8")
            self._git("add", "--", rel)
            staged = self._git("diff", "--cached", "--quiet", check=False)
            if staged.returncode == 0:
                return True
            self._git(
                "-c", f"user.name={self.author_name}",
                "-c", f"user.email={self.author_email}",
                "commit", "-m", message, "--", rel,
            )
            pushed = self._git("push", self.remote, f"HEAD:{self.branch}", check=False)
            if pushed.returncode == 0:
                return True
            log.warning("voice release: article-page push race lost (%d/%d)", attempt, self.attempts)
        return False


class ReleasePreparer:
    """Summary -> page -> alert for one already-durably-claimed article."""

    def __init__(
        self,
        *,
        summarizer: SummaryProvider,
        publisher: PagePublisher,
        renderer=render_release_page,
    ):
        self.summarizer = summarizer
        self.publisher = publisher
        self.renderer = renderer

    def prepare(self, article: VoiceArticle, registry, *, voice_ids) -> PreparedRelease:
        writers = voice_names(article, registry, voice_ids=voice_ids)
        model_used = isinstance(self.summarizer, GeminiSummaryProvider)
        summary_fallback = False
        fallback_reason = ""

        try:
            summary = self.summarizer.summarize(article, writers=writers)
            # Gemini provider deliberately declines the model on thin metadata.
            if isinstance(self.summarizer, GeminiSummaryProvider):
                _material, rich_enough = source_material(article)
                model_used = rich_enough
        except Exception as exc:  # model failure must never reopen a durable claim
            log.warning("voice release: summary failed for %s: %s", article.key, exc)
            summary_fallback = True
            model_used = False
            fallback_reason = "Model summary generation was unavailable."
            summary = metadata_summary(article, writers=writers, reason=fallback_reason)

        page_path = article_page_path(article)
        page_url = article_page_url(article)
        try:
            page_html = self.renderer(article, writers=writers, summary=summary)
            published = self.publisher.publish(
                page_path,
                page_html,
                f"chore(voices): publish article summary {article_token(article)}",
            )
        except Exception as exc:  # rendering/publishing cannot corrupt the claim
            log.warning("voice release: page preparation failed for %s: %s", article.key, exc)
            published = False
            fallback_reason = f"page preparation failed: {type(exc).__name__}"

        click = page_url if published else original_url(article)
        alert = build_release_alert(
            article, writers=writers, summary=summary, click=click
        )
        return PreparedRelease(
            alert=alert,
            page_published=published,
            model_used=model_used,
            summary_fallback=summary_fallback,
            fallback_reason=fallback_reason,
        )
