from __future__ import annotations

import json
import html
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

from .config import Settings


@dataclass
class SourceItem:
    channel: str
    source: str
    title: str
    url: str
    published_at: str | None
    summary: str


def strip_html(value: str) -> str:
    text = html.unescape(value or "")
    text = text.replace("\xa0", " ").replace("&nbsp;", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError, IndexError):
        return value


def fetch_rss(url: str, timeout_seconds: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "trend-banner-automation/0.1"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def fetch_json(
    url: str,
    timeout_seconds: int,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict | None = None,
) -> dict:
    data = None
    request_headers = {"User-Agent": "trend-banner-automation/0.1"}
    if headers:
        request_headers.update(headers)
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")

    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:  # noqa: BLE001
            detail = ""
        if detail:
            raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {detail}") from exc
        raise


def parse_rss_items(payload: bytes, source_name: str, channel: str, limit: int) -> list[SourceItem]:
    root = ET.fromstring(payload)
    items: list[SourceItem] = []
    for item in root.findall(".//item")[:limit]:
        title = strip_html(item.findtext("title", default=""))
        link = item.findtext("link", default="")
        summary = strip_html(item.findtext("description", default=""))
        published_at = parse_date(item.findtext("pubDate"))
        if title:
            items.append(
                SourceItem(
                    channel=channel,
                    source=source_name,
                    title=title,
                    url=link,
                    published_at=published_at,
                    summary=summary,
                )
            )
    return items


def parse_manual_signals(path: Path) -> list[SourceItem]:
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    items: list[SourceItem] = []
    current: dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line.startswith("- channel:"):
            if current.get("title"):
                items.append(_manual_item(current))
            current = {"channel": line.split(":", 1)[1].strip()}
        elif ":" in line and current:
            key, value = line.split(":", 1)
            current[key.strip()] = value.strip()
    if current.get("title"):
        items.append(_manual_item(current))
    return items


def collect_youtube(settings: Settings, queries: list[str]) -> tuple[list[SourceItem], list[str]]:
    if not settings.enable_youtube:
        return [], []
    if not settings.youtube_api_key:
        return [], ["YouTube Data API skipped: YOUTUBE_API_KEY is not configured."]

    errors: list[str] = []
    items: list[SourceItem] = []
    published_after = (datetime.utcnow() - timedelta(days=7)).replace(microsecond=0).isoformat() + "Z"

    for query in queries:
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": "date",
            "regionCode": "KR",
            "relevanceLanguage": "ko",
            "publishedAfter": published_after,
            "maxResults": str(min(settings.max_items_per_source, 10)),
            "key": settings.youtube_api_key,
        }
        url = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode(params)
        try:
            payload = fetch_json(url, settings.fetch_timeout_seconds)
            for entry in payload.get("items", []):
                snippet = entry.get("snippet", {})
                video_id = entry.get("id", {}).get("videoId", "")
                title = strip_html(snippet.get("title", ""))
                if not title:
                    continue
                items.append(
                    SourceItem(
                        channel="diffusion",
                        source=f"YouTube Search - {query}",
                        title=title,
                        url=f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
                        published_at=snippet.get("publishedAt"),
                        summary=strip_html(snippet.get("description", "")),
                    )
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"YouTube Search - {query}: {exc}")

    return items, errors


def collect_naver_datalab(
    settings: Settings,
    datalab_config: dict,
) -> tuple[list[SourceItem], list[str]]:
    if not settings.enable_naver_datalab:
        return [], []
    if not settings.naver_client_id or not settings.naver_client_secret:
        return [], ["Naver DataLab skipped: NAVER_CLIENT_ID or NAVER_CLIENT_SECRET is not configured."]

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    body = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "timeUnit": datalab_config.get("timeUnit", "date"),
        "keywordGroups": datalab_config.get("keywordGroups", [])[:5],
    }
    headers = {
        "X-Naver-Client-Id": settings.naver_client_id,
        "X-Naver-Client-Secret": settings.naver_client_secret,
        "Content-Type": "application/json",
    }
    try:
        payload = fetch_json(
            "https://openapi.naver.com/v1/datalab/search",
            settings.fetch_timeout_seconds,
            method="POST",
            headers=headers,
            body=body,
        )
    except Exception as exc:  # noqa: BLE001
        return [], [f"Naver DataLab: {exc}"]

    items: list[SourceItem] = []
    for result in payload.get("results", []):
        title = result.get("title", "")
        keywords = ", ".join(result.get("keywords", []))
        data_points = result.get("data", [])
        latest = data_points[-1] if data_points else {}
        peak = max((point.get("ratio", 0) for point in data_points), default=0)
        if title:
            items.append(
                SourceItem(
                    channel="validation",
                    source="Naver DataLab",
                    title=f"{title} 검색 추이",
                    url="https://datalab.naver.com/",
                    published_at=latest.get("period"),
                    summary=(
                        f"keywords: {keywords}; latest_ratio: {latest.get('ratio', 'n/a')}; "
                        f"seven_day_peak_ratio: {peak}"
                    ),
                )
            )
    return items, []


def collect_naver_search(
    settings: Settings,
    search_configs: list[dict],
) -> tuple[list[SourceItem], list[str]]:
    if not settings.naver_client_id or not settings.naver_client_secret:
        return [], ["Naver Search skipped: NAVER_CLIENT_ID or NAVER_CLIENT_SECRET is not configured."]

    headers = {
        "X-Naver-Client-Id": settings.naver_client_id,
        "X-Naver-Client-Secret": settings.naver_client_secret,
    }
    items: list[SourceItem] = []
    errors: list[str] = []
    for config in search_configs:
        service = config.get("service", "news")
        query = config.get("query", "")
        channel = config.get("channel", "validation")
        if not query:
            continue
        params = urllib.parse.urlencode(
            {
                "query": query,
                "display": str(min(int(config.get("display", 10)), settings.max_items_per_source)),
                "sort": config.get("sort", "date"),
            }
        )
        url = f"https://openapi.naver.com/v1/search/{service}.json?{params}"
        try:
            payload = fetch_json(url, settings.fetch_timeout_seconds, headers=headers)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Naver Search - {service}/{query}: {exc}")
            continue

        for entry in payload.get("items", []):
            title = strip_html(entry.get("title", ""))
            summary = strip_html(entry.get("description", ""))
            link = entry.get("link", "")
            published_at = parse_date(entry.get("pubDate")) if entry.get("pubDate") else None
            if title:
                items.append(
                    SourceItem(
                        channel=channel,
                        source=f"Naver Search {service} - {query}",
                        title=title,
                        url=link,
                        published_at=published_at,
                        summary=summary,
                    )
                )
    return items, errors


def _manual_item(current: dict[str, str]) -> SourceItem:
    return SourceItem(
        channel=current.get("channel", "initial"),
        source=current.get("source", "manual"),
        title=current.get("title", ""),
        url=current.get("source", ""),
        published_at=current.get("date"),
        summary=current.get("note", ""),
    )


def collect_sources(settings: Settings) -> tuple[list[SourceItem], list[str]]:
    errors: list[str] = []
    if not settings.source_config.exists():
        return [], [f"Source config not found: {settings.source_config}"]

    config = json.loads(settings.source_config.read_text(encoding="utf-8"))
    collected: list[SourceItem] = []

    for source in config.get("rss_sources", []):
        try:
            payload = fetch_rss(source["url"], settings.fetch_timeout_seconds)
            collected.extend(
                parse_rss_items(
                    payload=payload,
                    source_name=source["name"],
                    channel=source["channel"],
                    limit=settings.max_items_per_source,
                )
            )
        except Exception as exc:  # noqa: BLE001 - source failures should be reported, not fatal
            errors.append(f"{source.get('name', 'unknown')}: {exc}")

    youtube_items, youtube_errors = collect_youtube(settings, config.get("youtube_queries", []))
    collected.extend(youtube_items)
    errors.extend(youtube_errors)

    naver_search_items, naver_search_errors = collect_naver_search(
        settings,
        config.get("naver_search", []),
    )
    collected.extend(naver_search_items)
    errors.extend(naver_search_errors)

    naver_items, naver_errors = collect_naver_datalab(settings, config.get("naver_datalab", {}))
    collected.extend(naver_items)
    errors.extend(naver_errors)

    manual_signal_file = config.get("manual_signal_file")
    if manual_signal_file:
        collected.extend(parse_manual_signals(settings.root_dir / manual_signal_file))

    return collected, errors


def render_source_brief(items: list[SourceItem], errors: list[str]) -> str:
    now = datetime.now().isoformat(timespec="seconds")
    lines = [f"# Source Brief", "", f"Collected at: {now}", ""]

    if errors:
        lines.extend(["## Source Access Issues", ""])
        for error in errors:
            lines.append(f"- {error}")
        lines.append("")

    if not items:
        lines.extend(
            [
                "## Collected Items",
                "",
                "No source items were collected. The report must clearly mark source access as unavailable.",
            ]
        )
        return "\n".join(lines)

    lines.extend(["## Collected Items", ""])
    for item in items:
        lines.extend(
            [
                f"- channel: {item.channel}",
                f"  source: {item.source}",
                f"  date: {item.published_at or 'unknown'}",
                f"  title: {item.title}",
                f"  url: {item.url}",
                f"  summary: {item.summary[:500]}",
            ]
        )
    return "\n".join(lines)
