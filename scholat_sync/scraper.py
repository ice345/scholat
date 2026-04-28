"""学者网通用栏目抓取与日程解析模块。"""

import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .config import SECTION_KEYWORDS, SCHOLAT_HOME_URL, STATE_FILE
from .models import ScheduleItem


def extract_section_links(home_html: str) -> list[tuple[str, str]]:
    """从首页提取目标栏目链接。"""
    soup = BeautifulSoup(home_html, "html.parser")
    links: list[tuple[str, str]] = []

    for anchor in soup.find_all("a", href=True):
        text = " ".join(anchor.get_text(" ", strip=True).split())
        href = anchor["href"].strip()
        if not text or not href:
            continue
        for keyword in SECTION_KEYWORDS:
            if keyword in text:
                links.append((keyword, href))

    dedup: dict[str, tuple[str, str]] = {}
    for section, href in links:
        abs_url = urljoin(SCHOLAT_HOME_URL, href)
        dedup[f"{section}|{abs_url}"] = (section, abs_url)

    return list(dedup.values())


def parse_datetime_from_text(text: str) -> Optional[tuple[datetime, datetime]]:
    """从文本中解析日期时间。

    支持：
    - 2026-04-11 / 2026年4月11日 09:00
    - 4月11日 09:00

    返回：
    - (start_dt, end_dt)；若无法识别返回 None。
    """
    text = " ".join(text.split())

    m1 = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})[日]?\s*(\d{1,2}:\d{2})?", text)
    if m1:
        year = int(m1.group(1))
        month = int(m1.group(2))
        day = int(m1.group(3))
        hhmm = m1.group(4) or "09:00"
        hour, minute = [int(x) for x in hhmm.split(":")]
        start = datetime(year, month, day, hour, minute)
        return start, start + timedelta(hours=1)

    m2 = re.search(r"(\d{1,2})月(\d{1,2})日\s*(\d{1,2}:\d{2})?", text)
    if m2:
        now = datetime.now()
        month = int(m2.group(1))
        day = int(m2.group(2))
        hhmm = m2.group(3) or "09:00"
        hour, minute = [int(x) for x in hhmm.split(":")]
        start = datetime(now.year, month, day, hour, minute)
        if start < now - timedelta(days=180):
            start = start.replace(year=now.year + 1)
        return start, start + timedelta(hours=1)

    return None


def scrape_schedule_items(section: str, page_url: str, page_html: str, limit: int) -> list[ScheduleItem]:
    """从页面中抽取可识别时间的日程条目。"""
    soup = BeautifulSoup(page_html, "html.parser")
    items: list[ScheduleItem] = []
    seen = set()

    for node in soup.select("li, tr, p, div"):
        text = " ".join(node.get_text(" ", strip=True).split())
        if len(text) < 8 or len(text) > 220:
            continue

        dt = parse_datetime_from_text(text)
        if not dt:
            continue

        anchor = node.find("a", href=True)
        source_url = page_url if not anchor else urljoin(page_url, anchor["href"].strip())

        title_text = text[:50]
        if anchor and anchor.get_text(strip=True):
            title_text = anchor.get_text(strip=True)[:50]

        key = f"{title_text}|{dt[0].isoformat()}|{source_url}"
        if key in seen:
            continue
        seen.add(key)

        items.append(
            ScheduleItem(
                title=title_text,
                source_section=section,
                source_url=source_url,
                text=text,
                start_dt=dt[0],
                end_dt=dt[1],
            )
        )

        if len(items) >= limit:
            break

    return items


def load_state(path: str = STATE_FILE) -> dict:
    """读取本地同步状态文件（用于去重）。"""
    if not os.path.exists(path):
        return {"fingerprints": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(path: str, state: dict) -> None:
    """保存本地同步状态文件。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def fingerprint(item: ScheduleItem) -> str:
    """为日程条目生成稳定指纹，用于去重。"""
    raw = f"{item.title}|{item.start_dt.isoformat()}|{item.source_url}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()
