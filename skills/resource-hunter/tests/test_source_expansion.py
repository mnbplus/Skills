from __future__ import annotations

import json
from resource_hunter.core import AnimeToshoSource, DaliPanSource, DMHYSource, PanSearchSource, ResourceHunterEngine, TorlockSource, build_plan, parse_intent, score_result, search_indexed_discovery


class FakeHTTPClient:
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping

    def get_text(self, url: str, timeout: int | None = None) -> str:
        for key, value in self.mapping.items():
            if key in url:
                return value
        if "api.dalipan.com/api/v1/pan/search" in url:
            return DALIPAN_JSON
        raise RuntimeError(f"no fixture for {url}")

    def get_json(self, url: str, timeout: int | None = None):
        return json.loads(self.get_text(url, timeout=timeout))


ANIMETOSHO_RSS = """<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0'>
  <channel>
    <item>
      <title>[VCB-Studio] Attack on Titan Season 1 1080p</title>
      <description><![CDATA[<strong>Total Size</strong>: 10.5 GB<br/><strong>Download Links</strong>: <a href="magnet:?xt=urn:btih:ABCDEF1234567890">Magnet</a>]]></description>
      <link>https://animetosho.org/view/attack-on-titan-s1</link>
      <enclosure url="https://storage.animetosho.org/torrent/aot-season1.torrent" type="application/x-bittorrent" length="0" />
    </item>
  </channel>
</rss>"""

DMHY_HTML = """
<table><tbody>
<tr>
<td class="title">
<a href="/topics/view/704046_attack_on_titan" target="_blank">[VCB-Studio] Attack on Titan / Shingeki no Kyojin 1080p</a>
</td>
<td nowrap="nowrap" align="center">
<a class="download-arrow arrow-magnet" href="magnet:?xt=urn:btih:1234567890ABCDEF">&nbsp;</a>
</td>
<td nowrap="nowrap" align="center">170.3GB</td>
</tr>
</tbody></table>
"""

TORLOCK_SEARCH_HTML = """
<table>
<tr>
<td><div><a href=/torrent/123/attack-on-titan-season-1.html><b>Attack on Titan Season 1</b> 1080p</a></div></td>
<td class=td>4/7/2025</td><td class=ts>131.6 GB</td><td class=tul>321</td><td class=tdl>45</td>
</tr>
</table>
"""

TORLOCK_DETAIL_HTML = """
<html><body><a href="magnet:?xt=urn:btih:FFEEDDCCBBAA99887766">Magnet Link</a></body></html>
"""

BING_HTML = """
<ol id="b_results">
<li class="b_algo"><h2><a href="https://pan.quark.cn/s/abc123">Attack on Titan Quark</a></h2></li>
<li class="b_algo"><h2><a href="https://tieba.baidu.com/p/123456">Attack on Titan Tieba</a></h2></li>
</ol>
"""

BRAVE_HTML = """
<div id="results">
  <div class="snippet"><a href="https://pan.baidu.com/s/xyz987" target="_self" class="svelte-14r20fy l1"><div class="title search-snippet-title">Attack on Titan Baidu Pan</div></a></div>
  <div class="snippet"><a href="magnet:?xt=urn:btih:FFEEDDCCBBAA" target="_self" class="svelte-14r20fy l1"><div class="title search-snippet-title">Attack on Titan Magnet Mirror</div></a></div>
</div>
"""

DALIPAN_JSON = """{
  "resources": [
    {
      "highs": {
        "filename": ["<mark>进击</mark><mark>的</mark><mark>巨人</mark>最终季"]
      },
      "res": {
        "id": "abc123id",
        "eu": "encrypted-token-001",
        "filename": "进击的巨人最终季",
        "size": "24549223169",
        "ctime": "2026-01-30 09:32:44",
        "updatetime": "2026-01-30 09:54:35",
        "category": 6,
        "type": "baidu",
        "filelist": [
          {"isdir": 1, "filename": "进击的巨人最终季"}
        ]
      }
    }
  ],
  "total": 1
}"""

PANSEARCH_HTML = r"""
<html><body>
<script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"data":{"total":2,"data":[{"id":29700,"content":"剧名：进击的巨人\n别名：Attack on Titan\n阿里云链接：<a class=\"resource-link\" target=\"_blank\" href=\"https://www.aliyundrive.com/s/qaQLuXwnTFw\">https://www.aliyundrive.com/s/qaQLuXwnTFw</a>\n提取码：7788","pan":"aliyundrive","image":"https://dl.pansearch.me/resources/1.jpg","time":"2021-11-13T10:54:40+08:00"},{"id":3227,"content":"中文名: 进击的巨人\n别名: Attack on Titan\n分享链接：\n<a class=\"resource-link\" target=\"_blank\" href=\"https://www.aliyundrive.com/s/RG1m85SWVpo\">https://www.aliyundrive.com/s/RG1m85SWVpo</a>","pan":"aliyundrive","image":"https://dl.pansearch.me/resources/2.jpg","time":"2021-08-06T08:03:48+08:00"}]},"limit":9},"__N_SSP":true},"page":"/search","query":{"keyword":"Attack on Titan"},"buildId":"b3d28aab680bcfde974b229185c6ca0fc8248c02"}</script>
</body></html>
"""


def test_build_plan_prioritizes_new_anime_sources():
    anime = parse_intent("Attack on Titan", explicit_kind="anime")
    plan = build_plan(anime)
    assert plan.preferred_torrent_sources[:4] == ["nyaa", "animetosho", "dmhy", "torlock"]
    assert plan.preferred_pan_sources[0] == "dalipan"
    assert "pansearch" in plan.preferred_pan_sources
    assert "animetosho" in plan.source_query_plan
    assert "dmhy" in plan.source_query_plan
    assert "torlock" in plan.source_query_plan
    assert "dalipan" in plan.source_query_plan
    assert "pansearch" in plan.source_query_plan


def test_engine_registers_new_torrent_sources():
    engine = ResourceHunterEngine()
    source_names = [source.name for source in engine.torrent_sources]
    pan_source_names = [source.name for source in engine.pan_sources]
    assert "animetosho" in source_names
    assert "dmhy" in source_names
    assert "torlock" in source_names
    assert "dalipan" in pan_source_names
    assert "pansearch" in pan_source_names


def test_animetosho_source_parses_rss_feed():
    source = AnimeToshoSource()
    results = source.search(
        "Attack on Titan",
        parse_intent("Attack on Titan", explicit_kind="anime"),
        limit=5,
        page=1,
        http_client=FakeHTTPClient({"feed.animetosho.org": ANIMETOSHO_RSS}),
    )
    assert results
    assert results[0].source == "animetosho"
    assert results[0].link_or_magnet.startswith("magnet:")
    assert results[0].size == "10.5 GB"


def test_dmhy_source_parses_html_rows():
    source = DMHYSource()
    results = source.search(
        "Attack on Titan",
        parse_intent("Attack on Titan", explicit_kind="anime"),
        limit=5,
        page=1,
        http_client=FakeHTTPClient({"dmhy.org": DMHY_HTML}),
    )
    assert results
    assert results[0].source == "dmhy"
    assert results[0].provider == "magnet"
    assert results[0].size == "170.3GB"


def test_torlock_source_parses_search_and_detail_pages():
    source = TorlockSource()
    results = source.search(
        "Attack on Titan",
        parse_intent("Attack on Titan", explicit_kind="anime"),
        limit=5,
        page=1,
        http_client=FakeHTTPClient(
            {
                "torlock2.com/all/torrents": TORLOCK_SEARCH_HTML,
                "torlock2.com/torrent/123": TORLOCK_DETAIL_HTML,
            }
        ),
    )
    assert results
    assert results[0].source == "torlock"
    assert results[0].provider == "magnet"
    assert results[0].size == "131.6 GB"
    assert results[0].seeders == 321


def test_torlock_source_skips_detail_failures_and_keeps_remaining_results():
    source = TorlockSource()
    results = source.search(
        "Attack on Titan",
        parse_intent("Attack on Titan", explicit_kind="anime"),
        limit=5,
        page=1,
        http_client=FakeHTTPClient(
            {
                "torlock2.com/all/torrents": TORLOCK_SEARCH_HTML + '<tr><td><div><a href=/torrent/999/broken.html><b>Broken Mirror</b></a></div></td><td class=td>4/7/2025</td><td class=ts>1.0 GB</td><td class=tul>10</td><td class=tdl>1</td></tr>',
                "torlock2.com/torrent/123": TORLOCK_DETAIL_HTML,
            }
        ),
    )
    assert any(item.source == "torlock" for item in results)


def test_dalipan_source_parses_public_api_payload():
    source = DaliPanSource()
    results = source.search(
        "进击的巨人",
        parse_intent("进击的巨人", explicit_kind="anime"),
        limit=5,
        page=1,
        http_client=FakeHTTPClient({"unused": "unused"}),
    )
    assert results
    assert results[0].source == "dalipan"
    assert results[0].provider == "baidu"
    assert results[0].raw["delivery"] == "token_only"
    assert results[0].raw["requires_follow_up"] is True
    assert results[0].raw["retrieval_role"] == "clue"
    assert results[0].raw["dalipan_transport"]["search"] in {"verified", "insecure_fallback"}
    assert results[0].raw["dalipan_follow_up"]["detail_status"] == "disabled"
    scored = score_result(results[0], parse_intent("进击的巨人", explicit_kind="anime"))
    assert scored.validation_status == "clue"
    assert scored.actionability == "clue"
    assert any("token-only result" in item for item in scored.validation_signals)
    assert any("final share URL may require follow-up" in item for item in scored.validation_signals)
    assert results[0].link_or_magnet.startswith("dalipan://baidu/")
    assert results[0].raw["dalipan_id"]


def test_dalipan_uses_insecure_fallback_only_for_ssl_like_failures():
    class SSLFirstHTTPClient(FakeHTTPClient):
        def __init__(self, mapping: dict[str, str]) -> None:
            super().__init__(mapping)
            self.json_calls = 0

        def get_json(self, url: str, timeout: int | None = None):
            self.json_calls += 1
            raise RuntimeError("SSL: CERTIFICATE_VERIFY_FAILED")

    source = DaliPanSource()
    client = SSLFirstHTTPClient({"unused": "unused"})
    results = source.search(
        "进击的巨人",
        parse_intent("进击的巨人", explicit_kind="anime"),
        limit=5,
        page=1,
        http_client=client,
    )
    assert results
    assert client.json_calls == 1
    assert results[0].raw["dalipan_transport"]["search"] == "insecure_fallback"


def test_dalipan_does_not_use_insecure_fallback_for_non_ssl_errors():
    class HTTP403Client(FakeHTTPClient):
        def get_json(self, url: str, timeout: int | None = None):
            raise RuntimeError("HTTP 403")

    source = DaliPanSource()
    try:
        source.search(
            "进击的巨人",
            parse_intent("进击的巨人", explicit_kind="anime"),
            limit=5,
            page=1,
            http_client=HTTP403Client({}),
        )
        assert False, "expected non-ssl error to propagate"
    except Exception as exc:
        assert "403" in str(exc)


def test_dalipan_optional_follow_up_auth_failure_stays_clue_only():
    class FollowUpRestrictedClient(FakeHTTPClient):
        def get_json(self, url: str, timeout: int | None = None):
            if "api.dalipan.com/api/v1/pan/detail" in url:
                from resource_hunter.errors import UpstreamError
                raise UpstreamError("login required", failure_kind="auth_required")
            if "api.dalipan.com/api/v1/pan/url" in url:
                return -1
            return super().get_json(url, timeout=timeout)

    source = DaliPanSource(enable_detail_follow_up=True, enable_final_url_follow_up=True)
    results = source.search(
        "进击的巨人",
        parse_intent("进击的巨人", explicit_kind="anime"),
        limit=5,
        page=1,
        http_client=FollowUpRestrictedClient({"unused": "unused"}),
    )
    assert results
    assert results[0].raw["delivery"] == "token_only"
    assert results[0].raw["requires_follow_up"] is True
    assert results[0].raw["dalipan_follow_up"]["detail_status"] == "auth_required"
    assert results[0].raw["dalipan_follow_up"]["final_url_status"] == "auth_required"


def test_pansearch_source_parses_next_data_cards_into_direct_results():
    source = PanSearchSource()
    results = source.search(
        "Attack on Titan",
        parse_intent("Attack on Titan", explicit_kind="anime"),
        limit=5,
        page=1,
        http_client=FakeHTTPClient({"pansearch.me/search?keyword": PANSEARCH_HTML}),
    )
    assert results
    assert results[0].source == "pansearch"
    assert results[0].provider == "aliyun"
    assert results[0].password == "7788"
    assert results[0].link_or_magnet.startswith("https://www.aliyundrive.com/s/")
    assert results[0].raw["pansearch_id"] == 29700
    assert results[0].raw["pansearch_pan"] == "aliyundrive"
    scored = score_result(results[0], parse_intent("Attack on Titan", explicit_kind="anime"))
    assert scored.actionability in {"actionable", "direct"}
    assert scored.validation_status in {"partial", "validated"}


def test_indexed_discovery_uses_bing_and_brave_html_results():
    intent = parse_intent("Attack on Titan", explicit_kind="anime")
    results = search_indexed_discovery(
        intent,
        FakeHTTPClient(
            {
                "duckduckgo.com": "<html></html>",
                "bing.com/search": BING_HTML,
                "search.brave.com/search": BRAVE_HTML,
            }
        ),
        max_results=10,
    )
    sources = {result.source for result in results}
    assert "search-index:bing" in sources
    assert "search-index:brave" in sources
    assert any(result.provider in {"quark", "baidu", "magnet", "tieba_thread"} for result in results)
