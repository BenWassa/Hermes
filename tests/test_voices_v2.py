"""Voices V2 product-tier registry and deterministic morning policy."""

from __future__ import annotations

import datetime as dt
import json

import requests

from src.voices.following import qualifies_selective, select_following
from src.voices.http import USER_AGENT, VoiceHttp
from src.voices.model import Attribution, EVIDENCE_SOURCE_SCOPE, VoiceArticle
from src.voices.registry import (
    Registry,
    TIER_CORE,
    TIER_DISCOVERY,
    TIER_SELECTIVE,
    Voice,
    load_registry,
    validate,
)

UTC = dt.timezone.utc
BASE = dt.datetime(2026, 9, 9, 12, tzinfo=UTC)

CORE_IDS = [
    "conrad-black",
    "andrew-coyne",
    "paul-wells",
    "ezra-klein",
    "david-brooks",
    "francis-fukuyama",
    "fareed-zakaria",
    "adam-tooze",
    "helen-thompson",
    "jonathan-haidt",
    "steven-pinker",
    "arthur-c-brooks",
    "tyler-cowen",
    "zeynep-tufekci",
    "dan-wang",
]

REACHABLE_PRIMARY_URLS = {
    "conrad-black": "https://www.nationalnewswatch.com/author/conrad-black",
    "andrew-coyne": "https://www.nationalnewswatch.com/author/andrew-coyne",
    "paul-wells": "https://www.nationalnewswatch.com/author/paul-wells",
    "ezra-klein": "https://www.nytimes.com/svc/collections/v1/publish/https://www.nytimes.com/by/ezra-klein/rss.xml",
    "david-brooks": "https://www.theatlantic.com/feed/author/david-brooks/",
    "francis-fukuyama": "https://www.persuasion.community/feed",
    "adam-tooze": "https://foreignpolicy.com/author/adam-tooze/feed/",
    "helen-thompson": "https://www.newstatesman.com/author/helen-thompson",
    "jonathan-haidt": "https://www.afterbabel.com/feed",
    "steven-pinker": "https://stevenpinker.com/publications",
    "arthur-c-brooks": "https://www.thefp.com/feed",
    "tyler-cowen": "https://marginalrevolution.com/marginalrevolution/author/tyler-cowen/feed",
    "zeynep-tufekci": "https://www.nytimes.com/svc/collections/v1/publish/https://www.nytimes.com/by/zeynep-tufekci/rss.xml",
    "dan-wang": "https://danwang.co/feed/",
}


def article(
    key: str,
    voice_id: str,
    minute: int,
    *,
    description: str | None = None,
    primary: bool = True,
) -> VoiceArticle:
    return VoiceArticle(
        key=key,
        title=f"A substantive argument from {voice_id} {key}",
        canonical_url=f"https://example.com/{key}",
        url=f"https://example.com/{key}",
        description=description if description is not None else ("A careful argument about public life. " * 8),
        published_at=BASE + dt.timedelta(minutes=minute),
        identity_keys=frozenset({f"url:https://example.com/{key}"}),
        attributions=[
            Attribution(
                voice_id=voice_id,
                evidence=EVIDENCE_SOURCE_SCOPE,
                detail="test",
            )
        ],
        syndication_primary=primary,
    )


def registry(*voices: Voice) -> Registry:
    return Registry(voices=tuple(voices))


def core(voice_id: str) -> Voice:
    return Voice(id=voice_id, name=voice_id.replace("-", " ").title(), tier=TIER_CORE)


def test_production_registry_has_exact_locked_tiers_and_explicit_tier_fields():
    raw = json.loads(open("data/voices.json", encoding="utf-8").read())
    assert all("tier" in voice for voice in raw["voices"])

    reg = load_registry("data/voices.json")
    assert [voice.id for voice in reg.voices if voice.tier == TIER_CORE] == CORE_IDS
    assert [voice.id for voice in reg.voices if voice.tier == TIER_SELECTIVE] == ["jordan-peterson"]
    assert [voice.id for voice in reg.voices if voice.tier == TIER_DISCOVERY] == ["george-monbiot"]


def test_production_core_primaries_match_live_corrected_source_contract():
    reg = load_registry("data/voices.json")
    for voice_id, expected_url in REACHABLE_PRIMARY_URLS.items():
        voice = reg.get(voice_id)
        assert voice is not None
        assert len(voice.enabled_sources) >= 1
        assert voice.enabled_sources[0].params.get("url") == expected_url

    fareed = reg.get("fareed-zakaria")
    assert fareed is not None
    assert fareed.tier == TIER_CORE
    assert fareed.enabled_sources == ()
    assert fareed.byline_publications == ("washingtonpost.com",)
    assert any(source.id == "washington-post-zakaria" and not source.enabled for source in fareed.sources)


def test_voice_http_uses_declared_application_user_agent_not_requests_default():
    session = requests.Session()
    assert session.headers["User-Agent"] != USER_AGENT
    VoiceHttp(session=session)
    assert session.headers["User-Agent"] == USER_AGENT


def test_legacy_notify_is_operational_state_not_tier_authority():
    reg = load_registry("data/voices.json")
    assert {voice.id for voice in reg.notifiable} == {
        "conrad-black",
        "jonathan-haidt",
        "jordan-peterson",
        "george-monbiot",
    }
    assert reg.get("george-monbiot").tier == TIER_DISCOVERY
    assert reg.get("jordan-peterson").tier == TIER_SELECTIVE
    assert reg.get("andrew-coyne").tier == TIER_CORE
    assert reg.get("andrew-coyne").notify is False

    watcher = reg.for_legacy_watcher()
    assert {voice.id for voice in watcher.voices} == {
        "conrad-black",
        "jonathan-haidt",
        "jordan-peterson",
        "george-monbiot",
    }


def test_zero_source_core_can_remain_registered_without_losing_membership():
    data = {
        "version": 1,
        "voices": [
            {
                "id": "zero-source-core",
                "name": "Zero Source",
                "tier": "core",
                "dormant": True,
                "notify": False,
            }
        ],
    }
    reg, problems = validate(data)
    assert problems == []
    assert reg.voices[0].tier == TIER_CORE
    assert reg.voices[0].enabled_sources == ()


def test_invalid_tier_is_rejected_without_consulting_notify():
    _reg, problems = validate(
        {
            "version": 1,
            "voices": [
                {
                    "id": "invalid-tier",
                    "name": "Invalid Tier",
                    "tier": "important",
                    "notify": True,
                    "dormant": True,
                }
            ],
        }
    )
    assert any(".tier 'important'" in problem for problem in problems)


def test_morning_registry_has_core_and_selective_but_not_discovery():
    reg = load_registry("data/voices.json")
    morning = reg.for_tiers({TIER_CORE, TIER_SELECTIVE})
    assert morning.get("jordan-peterson") is not None
    assert morning.get("george-monbiot") is None
    assert len([voice for voice in morning.voices if voice.tier == TIER_CORE]) == 15


def test_six_core_voices_fill_normal_ceiling_before_selective():
    voices = [core(f"core-{n}") for n in range(6)] + [
        Voice(id="selective-one", name="Selective One", tier=TIER_SELECTIVE)
    ]
    reg = registry(*voices)
    items = [article(f"c{n}", f"core-{n}", n) for n in range(6)]
    items.append(article("s", "selective-one", 100))

    chosen = select_following(items, cap=6, per_voice=2, registry=reg, overflow_cap=8)
    assert len(chosen) == 6
    assert {a.voice_ids[0] for a in chosen} == {f"core-{n}" for n in range(6)}


def test_five_core_voices_leave_one_normal_slot_for_qualified_selective():
    voices = [core(f"core-{n}") for n in range(5)] + [
        Voice(id="selective-one", name="Selective One", tier=TIER_SELECTIVE)
    ]
    reg = registry(*voices)
    items = [article(f"c{n}", f"core-{n}", n) for n in range(5)]
    items.append(article("s", "selective-one", 100))

    chosen = select_following(items, cap=6, per_voice=2, registry=reg, overflow_cap=8)
    assert len(chosen) == 6
    assert any(a.voice_ids[0] == "selective-one" for a in chosen)


def test_seventh_and_eighth_slots_are_core_breadth_only():
    voices = [core(f"core-{n}") for n in range(8)] + [
        Voice(id="selective-one", name="Selective One", tier=TIER_SELECTIVE)
    ]
    reg = registry(*voices)
    items = [article(f"c{n}", f"core-{n}", n) for n in range(8)]
    items.append(article("s", "selective-one", 1000))

    chosen = select_following(items, cap=6, per_voice=2, registry=reg, overflow_cap=8)
    assert len(chosen) == 8
    assert {a.voice_ids[0] for a in chosen} == {f"core-{n}" for n in range(8)}


def test_ninth_distinct_core_is_bounded_out_by_eight_item_hard_ceiling():
    voices = [core(f"core-{n}") for n in range(9)]
    reg = registry(*voices)
    items = [article(f"c{n}", f"core-{n}", n) for n in range(9)]

    chosen = select_following(items, cap=6, per_voice=2, registry=reg, overflow_cap=8)
    assert len(chosen) == 8
    assert "core-0" not in {a.voice_ids[0] for a in chosen}


def test_discovery_never_enters_tier_based_following():
    reg = registry(
        core("core-one"),
        Voice(id="discovery-one", name="Discovery One", tier=TIER_DISCOVERY),
    )
    chosen = select_following(
        [article("core", "core-one", 0), article("discovery", "discovery-one", 100)],
        cap=6,
        per_voice=2,
        registry=reg,
        overflow_cap=8,
    )
    assert [a.voice_ids[0] for a in chosen] == ["core-one"]


def test_selective_qualification_is_generic_deterministic_and_fails_closed():
    substantive = article("good", "selective-one", 0)
    short = article("short", "selective-one", 1, description="Brief note.")
    video = article(
        "video",
        "selective-one",
        2,
        description=("This video presents a long discussion of several questions. " * 5),
    )
    assert qualifies_selective(substantive) is True
    assert qualifies_selective(short) is False
    assert qualifies_selective(video) is False


def test_core_breadth_precedes_depth_and_secondary_syndication_is_ignored():
    reg = registry(core("core-one"), core("core-two"), core("core-three"))
    items = [
        article("one-new", "core-one", 100),
        article("one-second", "core-one", 90),
        article("one-third", "core-one", 80),
        article("two", "core-two", 10),
        article("three", "core-three", 0),
        article("copy", "core-two", 200, primary=False),
    ]
    chosen = select_following(items, cap=4, per_voice=2, registry=reg, overflow_cap=8)
    assert len(chosen) == 4
    assert {"core-one", "core-two", "core-three"} <= {a.voice_ids[0] for a in chosen}
    assert "copy" not in {a.key for a in chosen}
