"""Read-only YouTube channel analytics collector.

Uses only OAuth scopes:
- https://www.googleapis.com/auth/youtube.readonly
- https://www.googleapis.com/auth/yt-analytics.readonly
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
DATA_API = "https://www.googleapis.com/youtube/v3"
ANALYTICS_API = "https://youtubeanalytics.googleapis.com/v2/reports"
TIMEOUT_SECONDS = 30


class YouTubeAPIError(RuntimeError):
    pass


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise YouTubeAPIError(f"Missing required secret: {name}")
    return value


def refresh_access_token() -> str:
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": require_env("YOUTUBE_OAUTH_CLIENT_ID"),
            "client_secret": require_env("YOUTUBE_OAUTH_CLIENT_SECRET"),
            "refresh_token": require_env("YOUTUBE_OAUTH_REFRESH_TOKEN"),
            "grant_type": "refresh_token",
        },
        timeout=TIMEOUT_SECONDS,
    )
    if not response.ok:
        raise YouTubeAPIError(
            f"OAuth refresh failed: HTTP {response.status_code}; "
            "check the client and refresh-token secrets"
        )
    token = response.json().get("access_token")
    if not token:
        raise YouTubeAPIError("OAuth response did not include an access token")
    return str(token)


class YouTubeClient:
    def __init__(self, access_token: str) -> None:
        self.headers = {"Authorization": f"Bearer {access_token}"}

    def get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=TIMEOUT_SECONDS,
        )
        if not response.ok:
            message = response.text[:500].replace("\n", " ")
            raise YouTubeAPIError(
                f"YouTube API request failed: HTTP {response.status_code}: {message}"
            )
        return response.json()

    def channel(self) -> dict[str, Any]:
        data = self.get(
            f"{DATA_API}/channels",
            {"part": "snippet,contentDetails,statistics", "mine": "true"},
        )
        items = data.get("items", [])
        if not items:
            raise YouTubeAPIError("No YouTube channel was found for this OAuth user")
        return items[0]

    def uploaded_video_ids(self, playlist_id: str, limit: int) -> list[str]:
        ids: list[str] = []
        page_token: str | None = None
        while len(ids) < limit:
            params: dict[str, Any] = {
                "part": "contentDetails",
                "playlistId": playlist_id,
                "maxResults": min(50, limit - len(ids)),
            }
            if page_token:
                params["pageToken"] = page_token
            data = self.get(f"{DATA_API}/playlistItems", params)
            ids.extend(
                item["contentDetails"]["videoId"]
                for item in data.get("items", [])
                if item.get("contentDetails", {}).get("videoId")
            )
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return ids[:limit]

    def videos(self, video_ids: list[str]) -> list[dict[str, Any]]:
        if not video_ids:
            return []
        data = self.get(
            f"{DATA_API}/videos",
            {
                "part": "snippet,contentDetails,statistics,status",
                "id": ",".join(video_ids),
                "maxResults": 50,
            },
        )
        return data.get("items", [])

    def analytics(
        self,
        start_date: str,
        end_date: str,
        metrics: str,
        *,
        dimensions: str | None = None,
        filters: str | None = None,
        sort: str | None = None,
        max_results: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": metrics,
        }
        if dimensions:
            params["dimensions"] = dimensions
        if filters:
            params["filters"] = filters
        if sort:
            params["sort"] = sort
        if max_results:
            params["maxResults"] = max_results
        return self.get(ANALYTICS_API, params)


def rows_as_dicts(report: dict[str, Any]) -> list[dict[str, Any]]:
    headers = [header["name"] for header in report.get("columnHeaders", [])]
    return [dict(zip(headers, row)) for row in report.get("rows", [])]


def number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def build_insights(video_rows: list[dict[str, Any]]) -> list[str]:
    if not video_rows:
        return ["분석 기간에 영상별 성과 데이터가 없습니다."]

    ranked = sorted(video_rows, key=lambda row: number(row.get("views")), reverse=True)
    best = ranked[0]
    insights = [
        f"조회수 1위 영상은 {best.get('video', 'unknown')}이며 "
        f"{int(number(best.get('views'))):,}회입니다."
    ]

    weighted_views = sum(number(row.get("views")) for row in video_rows)
    if weighted_views:
        avg_percentage = sum(
            number(row.get("averageViewPercentage")) * number(row.get("views"))
            for row in video_rows
        ) / weighted_views
        insights.append(f"조회수 가중 평균 시청률은 {avg_percentage:.1f}%입니다.")

    gained = sum(number(row.get("subscribersGained")) for row in video_rows)
    lost = sum(number(row.get("subscribersLost")) for row in video_rows)
    insights.append(f"분석 영상의 구독자 순증은 {int(gained - lost):,}명입니다.")
    return insights


def markdown_summary(payload: dict[str, Any]) -> str:
    channel = payload["channel"]
    period = payload["period"]
    lines = [
        "# YouTube 채널 분석",
        "",
        f"- 채널: {channel['title']}",
        f"- 채널 ID: {channel['id']}",
        f"- 기간: {period['start_date']} ~ {period['end_date']}",
        f"- 분석 영상 수: {len(payload['video_metrics'])}",
        "",
        "## 자동 인사이트",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["insights"])
    lines.extend(
        [
            "",
            "## 영상별 성과",
            "",
            "| video_id | views | avg_view_% | subs_net | likes | comments |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in sorted(
        payload["video_metrics"],
        key=lambda item: number(item.get("views")),
        reverse=True,
    ):
        net = number(row.get("subscribersGained")) - number(
            row.get("subscribersLost")
        )
        lines.append(
            f"| {row.get('video', '')} | {int(number(row.get('views')))} | "
            f"{number(row.get('averageViewPercentage')):.1f} | {int(net)} | "
            f"{int(number(row.get('likes')))} | {int(number(row.get('comments')))} |"
        )
    if payload["warnings"]:
        lines.extend(["", "## 경고", ""])
        lines.extend(f"- {warning}" for warning in payload["warnings"])
    lines.append("")
    return "\n".join(lines)


def collect(days: int, max_videos: int) -> dict[str, Any]:
    client = YouTubeClient(refresh_access_token())
    today = date.today()
    start = today - timedelta(days=days - 1)
    start_date, end_date = start.isoformat(), today.isoformat()

    channel = client.channel()
    uploads = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    video_ids = client.uploaded_video_ids(uploads, max_videos)
    video_details = client.videos(video_ids)
    warnings: list[str] = []

    channel_metrics = rows_as_dicts(
        client.analytics(
            start_date,
            end_date,
            (
                "views,estimatedMinutesWatched,averageViewDuration,"
                "averageViewPercentage,likes,comments,shares,"
                "subscribersGained,subscribersLost"
            ),
        )
    )

    video_metrics: list[dict[str, Any]] = []
    if video_ids:
        try:
            video_metrics = rows_as_dicts(
                client.analytics(
                    start_date,
                    end_date,
                    (
                        "views,estimatedMinutesWatched,averageViewDuration,"
                        "averageViewPercentage,likes,comments,shares,"
                        "subscribersGained,subscribersLost"
                    ),
                    dimensions="video",
                    filters=f"video=={','.join(video_ids)}",
                    sort="-views",
                    max_results=max_videos,
                )
            )
        except YouTubeAPIError as exc:
            warnings.append(f"영상별 Analytics를 가져오지 못했습니다: {exc}")

    retention: dict[str, list[dict[str, Any]]] = {}
    for video_id in [row.get("video") for row in video_metrics[:5]]:
        if not video_id:
            continue
        try:
            report = client.analytics(
                start_date,
                end_date,
                "audienceWatchRatio,relativeRetentionPerformance",
                dimensions="elapsedVideoTimeRatio",
                filters=f"video=={video_id}",
            )
            retention[str(video_id)] = rows_as_dicts(report)
        except YouTubeAPIError as exc:
            warnings.append(f"{video_id} 유지율을 가져오지 못했습니다: {exc}")

    detail_by_id = {
        item["id"]: {
            "title": item.get("snippet", {}).get("title"),
            "published_at": item.get("snippet", {}).get("publishedAt"),
            "duration": item.get("contentDetails", {}).get("duration"),
            "public_statistics": item.get("statistics", {}),
        }
        for item in video_details
    }

    payload: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": today.isoformat(),
        "period": {"start_date": start_date, "end_date": end_date, "days": days},
        "channel": {
            "id": channel["id"],
            "title": channel.get("snippet", {}).get("title", ""),
            "statistics": channel.get("statistics", {}),
        },
        "channel_metrics": channel_metrics,
        "video_metrics": video_metrics,
        "video_details": detail_by_id,
        "retention": retention,
        "insights": build_insights(video_metrics),
        "warnings": warnings,
    }
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=28)
    parser.add_argument("--max-videos", type=int, default=20)
    parser.add_argument("--output-dir", default="youtube_analytics_output")
    args = parser.parse_args()
    if not 1 <= args.days <= 365:
        parser.error("--days must be between 1 and 365")
    if not 1 <= args.max_videos <= 50:
        parser.error("--max-videos must be between 1 and 50")
    return args


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        payload = collect(args.days, args.max_videos)
    except YouTubeAPIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    (output_dir / "youtube_channel_analytics.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "youtube_channel_summary.md").write_text(
        markdown_summary(payload),
        encoding="utf-8",
    )
    print(
        f"Collected {len(payload['video_metrics'])} video rows for "
        f"{payload['channel']['title']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
