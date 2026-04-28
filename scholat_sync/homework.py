"""学者网作业页解析模块。"""

import hashlib
import json
import os
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .config import HOMEWORK_STATE_FILE
from .models import HomeworkItem


def parse_deadline(text: str) -> Optional[datetime]:
    """从截止时间文本中提取日期并标准化到 20:00。"""
    m = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", text)
    if not m:
        return None
    year, month, day = map(int, m.groups())
    return datetime(year, month, day, 20, 0, 0)


def parse_homework_page(html: str, base_url: str) -> list[HomeworkItem]:
    """解析作业列表页面，提取作业条目。

    页面结构变化时提供 fallback：先尝试表头匹配，失败后尝试通用行解析。
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = []

    # 策略 1：精确匹配表头（"作业标题" + "截止时间"）
    for candidate in soup.find_all("table"):
        headers = [th.get_text(" ", strip=True) for th in candidate.find_all("th")]
        if "作业标题" in headers and "截止时间" in headers:
            rows = candidate.find_all("tr")[1:]
            break

    # 策略 2（fallback）：找任意包含 "截止" 的表
    if not rows:
        for candidate in soup.find_all("table"):
            headers_text = " ".join(
                th.get_text(" ", strip=True) for th in candidate.find_all("th")
            )
            if "截止" in headers_text:
                print("[WARN] 未精确匹配'作业标题'，通过'截止'关键词兜底匹配")
                rows = candidate.find_all("tr")[1:]
                break

    if not rows:
        return []

    items: list[HomeworkItem] = []
    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue

        status = tds[0].get_text(" ", strip=True)
        title = tds[1].get_text(" ", strip=True)
        publisher = tds[2].get_text(" ", strip=True)
        deadline_text = tds[3].get_text(" ", strip=True)

        # 如果没有标题则跳过
        if not title:
            continue

        link = ""
        for a in tds[1].find_all("a", href=True):
            href = a["href"].strip()
            if "homeworkId=" in href:
                link = urljoin(base_url, href)
                break

        items.append(
            HomeworkItem(
                status=status,
                title=title,
                publisher=publisher,
                deadline_text=deadline_text,
                deadline_date=parse_deadline(deadline_text),
                detail_url=link or base_url,
            )
        )

    return items


def sort_by_deadline(items: list[HomeworkItem]) -> list[HomeworkItem]:
    """按截止时间升序排序；无截止时间的排在最后。"""
    return sorted(
        items,
        key=lambda hw: (hw.deadline_date is None, hw.deadline_date or datetime.max),
    )


def fingerprint(hw: HomeworkItem) -> str:
    """为作业条目生成稳定指纹（SHA1），用于去重和更新检测。"""
    raw = f"{hw.title}|{hw.deadline_date.isoformat() if hw.deadline_date else 'none'}|{hw.detail_url}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def load_state() -> dict:
    """读取作业同步状态文件。"""
    if not os.path.exists(HOMEWORK_STATE_FILE):
        return {"items": {}}
    try:
        with open(HOMEWORK_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[WARN] 状态文件损坏，将重新创建: {exc}")
        return {"items": {}}


def save_state(state: dict) -> None:
    """保存作业同步状态文件。"""
    with open(HOMEWORK_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
