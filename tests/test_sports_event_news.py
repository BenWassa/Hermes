import datetime as dt

from src.sports.event_news import EventArticle, fetch_guardian_event_articles, qualifies_event_article, select_event_articles
from src.sports.events import EVENT_REGISTRY

UTC = dt.timezone.utc


def spec(key):
    return next(item for item in EVENT_REGISTRY if item.key == key)


def article(event_key, title, *, hours=1, url=None):
    return EventArticle(
        event_key=event_key,
        title=title,
        description="",
        url=url or f"https://example.com/{abs(hash(title))}",
        source="The Guardian",
        published_at=dt.datetime(2028, 7, 20, 12, tzinfo=UTC) - dt.timedelta(hours=hours),
    )


def test_world_cup_requires_major_trigger_not_generic_preview():
    world = spec("fifa-world-cup-2030")
    assert qualifies_event_article(world, article(world.key, "World Cup preview: teams to watch")) is False
    assert qualifies_event_article(world, article(world.key, "Canada advances to World Cup quarter-final")) is True


def test_olympics_requires_canadian_medal_or_record_or_major_final():
    olympics = spec("summer-olympics-2028")
    assert qualifies_event_article(olympics, article(olympics.key, "Olympics swimming heats begin")) is False
    assert qualifies_event_article(olympics, article(olympics.key, "Canada wins bronze medal in rowing")) is True
    assert qualifies_event_article(olympics, article(olympics.key, "World record falls in Olympic final")) is True


def test_nfl_and_rugby_are_knockout_exception_only():
    nfl = spec("nfl-postseason")
    rugby = spec("rugby-world-cup-2027")
    assert qualifies_event_article(nfl, article(nfl.key, "NFL playoff practice notes")) is False
    assert qualifies_event_article(nfl, article(nfl.key, "Bills advance to AFC Championship")) is True
    assert qualifies_event_article(rugby, article(rugby.key, "Rugby World Cup pool standings update")) is False
    assert qualifies_event_article(rugby, article(rugby.key, "France eliminated in Rugby World Cup semi-final")) is True


def test_event_article_selection_dedupes_and_caps_at_two():
    olympics = spec("summer-olympics-2028")
    items = [
        article(olympics.key, "Canada wins gold medal in rowing", url="https://example.com/a?utm_source=x"),
        article(olympics.key, "Canada wins gold medal in rowing", hours=2, url="https://www.example.com/a?utm_medium=y"),
        article(olympics.key, "World record falls in Olympic final", hours=3),
        article(olympics.key, "Canada takes bronze medal in cycling", hours=4),
    ]
    selected = select_event_articles(olympics, items)
    assert len(selected) == 2
    assert selected[0].title == "Canada wins gold medal in rowing"
    assert selected[1].title == "World record falls in Olympic final"


class _Response:
    def __init__(self, title, *, fail=False):
        self.title = title
        self.fail = fail

    def raise_for_status(self):
        if self.fail:
            raise RuntimeError("boom")

    def json(self):
        return {
            "response": {
                "results": [
                    {
                        "webTitle": self.title,
                        "webUrl": "https://theguardian.com/example",
                        "webPublicationDate": "2028-07-20T11:00:00Z",
                        "fields": {"trailText": "Canada won a medal in the final."},
                    }
                ]
            }
        }


class _Session:
    def __init__(self):
        self.calls = []

    def get(self, url, *, params, timeout):
        self.calls.append((url, params, timeout))
        if "Olympic Games final record" in params["q"]:
            return _Response("World record falls in Olympic final")
        return _Response("Canada wins bronze medal in rowing")


def test_guardian_event_discovery_queries_only_active_event_registry(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    session = _Session()
    result = fetch_guardian_event_articles(
        on_date=dt.date(2028, 7, 20),
        since=dt.datetime(2028, 7, 19, tzinfo=UTC),
        until=dt.datetime(2028, 7, 21, tzinfo=UTC),
        session=session,
    )
    assert len(session.calls) == 2
    assert {call[1]["q"] for call in session.calls} == {"Olympics Canada medal", "Olympic Games final record"}
    assert "summer-olympics-2028" in result


def test_missing_guardian_key_means_zero_event_news_requests(monkeypatch):
    monkeypatch.delenv("GUARDIAN_API_KEY", raising=False)
    session = _Session()
    result = fetch_guardian_event_articles(
        on_date=dt.date(2028, 7, 20),
        since=dt.datetime(2028, 7, 19, tzinfo=UTC),
        until=dt.datetime(2028, 7, 21, tzinfo=UTC),
        session=session,
    )
    assert result == {}
    assert session.calls == []
