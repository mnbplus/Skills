from resource_hunter.core import deduplicate_results, format_search_text, fuse_result_evidence, parse_intent, score_result, validate_result
from resource_hunter.models import SearchResult


def test_pan_dedup_prefers_result_with_password():
    first = SearchResult(
        channel="pan",
        source="2fun",
        provider="aliyun",
        title="Movie A",
        link_or_magnet="https://example.com/share/abc",
        share_id_or_info_hash="abc",
        password="",
    )
    second = SearchResult(
        channel="pan",
        source="hunhepan",
        provider="aliyun",
        title="Movie A mirror",
        link_or_magnet="https://example.com/share/abc?pwd=1234",
        share_id_or_info_hash="abc",
        password="1234",
    )
    deduped = deduplicate_results([first, second])
    assert len(deduped) == 1
    assert deduped[0].password == "1234"


def test_torrent_score_rewards_match_quality_and_seeders():
    intent = parse_intent("Oppenheimer 2023", wants_4k=True)
    result = SearchResult(
        channel="torrent",
        source="yts",
        provider="magnet",
        title="Oppenheimer 2023 2160p HDR",
        link_or_magnet="magnet:?xt=urn:btih:abc",
        share_id_or_info_hash="abc",
        seeders=88,
    )
    scored = score_result(result, intent)
    assert scored.score > 80
    assert "4k requested" in scored.reasons
    assert "seeders" in scored.reasons


def test_year_conflict_downgrades_same_title_wrong_year_result():
    intent = parse_intent("The Merry Widow 1952", explicit_kind="movie")
    result = SearchResult(
        channel="torrent",
        source="tpb",
        provider="magnet",
        title="The Merry Widow 1934 720p WebDL X264",
        link_or_magnet="magnet:?xt=urn:btih:abc",
        share_id_or_info_hash="abc",
        seeders=25,
    )
    scored = score_result(result, intent)
    assert scored.validation_status == "conflict"
    assert scored.actionability == "speculative"
    assert any("year mismatch" in item for item in scored.penalties)
    assert any("year mismatch" in item for item in scored.validation_signals)
    assert scored.score < 100


def test_year_missing_downgrades_direct_to_actionable():
    intent = parse_intent("The Merry Widow 1952", explicit_kind="movie")
    result = SearchResult(
        channel="torrent",
        source="tpb",
        provider="magnet",
        title="The Merry Widow BluRay 1080p",
        link_or_magnet="magnet:?xt=urn:btih:def",
        share_id_or_info_hash="def",
    )
    scored = score_result(result, intent)
    assert scored.validation_status == "partial"
    assert scored.actionability == "actionable"
    assert any("year missing" in item for item in scored.validation_signals)


def test_validate_result_marks_manual_follow_up_as_clue():
    intent = parse_intent("赤橙黄绿青蓝紫 1982")
    result = SearchResult(
        channel="pan",
        source="tieba",
        provider="baidu_clue",
        title="赤橙黄绿青蓝紫",
        link_or_magnet="https://tieba.baidu.com/p/123",
        raw={
            "manual_follow_up": True,
            "delivery": "thread_clue",
            "retrieval_role": "clue",
            "requires_follow_up": True,
        },
    )
    validated = validate_result(result, intent)
    assert validated.validation_status == "clue"
    assert validated.actionability == "clue"
    assert any("follow-up clue" in item for item in validated.validation_signals)


def test_validate_result_keeps_passworded_follow_up_result_as_clue():
    intent = parse_intent("赤橙黄绿青蓝紫 1982")
    result = SearchResult(
        channel="pan",
        source="tieba",
        provider="baidu_clue",
        title="赤橙黄绿青蓝紫",
        link_or_magnet="https://tieba.baidu.com/p/123",
        password="y3bq",
        raw={
            "manual_follow_up": True,
            "delivery": "thread_clue",
            "retrieval_role": "clue",
            "requires_follow_up": True,
        },
    )
    validated = validate_result(result, intent)
    assert validated.validation_status == "clue"
    assert validated.actionability == "clue"
    assert any("follow-up clue" in item for item in validated.validation_signals)
    assert any("thread-level clue" in item for item in validated.validation_signals)


def test_validate_result_uses_delivery_semantics_for_token_only_clue():
    intent = parse_intent("进击的巨人", explicit_kind="anime")
    result = SearchResult(
        channel="pan",
        source="future-pan",
        provider="baidu",
        title="进击的巨人最终季",
        link_or_magnet="future://token/abc",
        raw={"delivery": "token_only", "requires_follow_up": True},
    )
    validated = validate_result(result, intent)
    assert validated.validation_status == "clue"
    assert validated.actionability == "clue"
    assert any("token-only result" in item for item in validated.validation_signals)
    assert any("final share URL may require follow-up" in item for item in validated.validation_signals)


def test_format_search_text_renders_generic_follow_up_note():
    text = format_search_text(
        {
            "query": "赤橙黄绿青蓝紫 1982",
            "intent": {"kind": "movie"},
            "plan": {"channels": ["pan"], "notes": []},
            "results": [
                SearchResult(
                    channel="pan",
                    source="tieba",
                    provider="baidu_clue",
                    title="赤橙黄绿青蓝紫",
                    link_or_magnet="https://tieba.baidu.com/p/123",
                    password="y3bq",
                    validation_status="clue",
                    actionability="clue",
                    match_bucket="title_family_match",
                    confidence=0.9,
                    score=41,
                    raw={"delivery": "thread_clue", "requires_follow_up": True},
                ).to_public_dict()
            ],
            "warnings": [],
            "source_status": [],
            "meta": {},
        }
    )
    assert "thread-level clue; open the thread and recover the final resource manually" in text


def test_fuse_result_evidence_promotes_corroborated_result():
    first = SearchResult(
        channel="pan",
        source="2fun",
        provider="aliyun",
        title="Movie A",
        link_or_magnet="https://example.com/share/abc",
        share_id_or_info_hash="abc",
        actionability="direct",
        validation_status="validated",
        score=80,
    )
    second = SearchResult(
        channel="pan",
        source="hunhepan",
        provider="aliyun",
        title="Movie A mirror",
        link_or_magnet="https://example.com/share/abc?pwd=1234",
        share_id_or_info_hash="abc",
        actionability="actionable",
        validation_status="validated",
        score=70,
        password="1234",
    )
    fused = fuse_result_evidence([first, second])
    assert len(fused) == 1
    assert fused[0].evidence_count == 2
    assert fused[0].corroboration_count == 1
    assert set(fused[0].corroborated_sources) == {"2fun", "hunhepan"}
    assert fused[0].cluster_id
    assert len(fused[0].supporting_results) == 2
