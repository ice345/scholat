"""学者网团队协作平台帖子抓取模块。

从 showTeamworkPostMessage.html 页面抓取团队帖子列表，
支持分页遍历与帖子详情获取。
"""

import re
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .models import TeamworkPost

TEAMWORK_BASE = "https://www.scholat.com/"


def fetch_teamwork_posts(
    session: requests.Session,
    team_id: int,
    change_to: str = "Ch",
    nav: int = 3,
    max_pages: Optional[int] = None,
) -> list[TeamworkPost]:
    """抓取指定团队的所有帖子（自动翻页）。

    参数：
    - session: 已登录的 requests.Session
    - team_id: 团队 ID
    - change_to: 编码参数，默认 Ch
    - nav: 导航标签，默认 3
    - max_pages: 最大抓取页数，None 表示抓取全部

    返回：
    - 帖子列表
    """
    posts: list[TeamworkPost] = []
    page = 1
    total_pages = 1

    while True:
        url = (
            f"{TEAMWORK_BASE}showTeamworkPostMessage.html"
            f"?id={team_id}&changeTo={change_to}&cpage={page}&nav={nav}"
        )
        resp = session.get(url, timeout=30)
        resp.raise_for_status()

        page_posts, total_pages = parse_teamwork_page(resp.text, team_id, url)
        posts.extend(page_posts)

        if max_pages is not None and page >= max_pages:
            break
        if page >= total_pages:
            break
        page += 1

    return posts


def parse_teamwork_page(
    html: str,
    team_id: int,
    source_url: str,
) -> tuple[list[TeamworkPost], int]:
    """解析团队协作平台帖子列表页。

    返回：
    - (帖子列表, 总页数)
    """
    soup = BeautifulSoup(html, "html.parser")
    posts: list[TeamworkPost] = []

    # 获取团队名称
    team_name = ""
    title_tag = soup.find("title")
    if title_tag:
        team_name = title_tag.get_text(strip=True).replace("团队协作平台", "").strip()

    # 解析帖子列表
    for news_div in soup.find_all("div", class_="news"):
        post = _parse_news_item(news_div, team_name, source_url)
        if post:
            posts.append(post)

    # 解析总页数
    total_pages = 1
    page_div = soup.find("div", class_="page")
    if page_div:
        match = re.search(r"共\s*(\d+)\s*页", page_div.get_text())
        if match:
            total_pages = int(match.group(1))

    return posts, total_pages


def _parse_news_item(
    news_div: BeautifulSoup,
    team_name: str,
    source_url: str,
) -> Optional[TeamworkPost]:
    """解析单个帖子 div.news。"""
    h3 = news_div.find("h3")
    if not h3:
        return None

    # 序号
    index = 0
    list_num = h3.find("span", class_="list_number")
    if list_num:
        match = re.search(r"(\d+)", list_num.get_text(strip=True))
        if match:
            index = int(match.group(1))

    # 标题与详情链接
    title = ""
    detail_url = ""
    anchor = h3.find("a", href=True)
    if anchor:
        title = anchor.get_text(strip=True)
        detail_url = urljoin(TEAMWORK_BASE, anchor["href"])

    # 元信息
    p_tag = news_div.find("p")
    ago_spans = p_tag.find_all("span", class_="ago") if p_tag else []

    visibility = ago_spans[0].get_text(strip=True) if len(ago_spans) > 0 else ""
    publisher = ago_spans[1].get_text(strip=True) if len(ago_spans) > 1 else ""
    publish_time = ago_spans[2].get_text(strip=True) if len(ago_spans) > 2 else ""
    view_count_text = ago_spans[3].get_text(strip=True) if len(ago_spans) > 3 else ""

    # 提取发布时间中的日期
    time_match = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", publish_time)
    if time_match:
        publish_time = time_match.group(1)

    # 提取浏览次数
    view_count = 0
    view_match = re.search(r"(\d+)", view_count_text)
    if view_match:
        view_count = int(view_match.group(1))

    return TeamworkPost(
        index=index,
        title=title,
        detail_url=detail_url,
        visibility=visibility,
        publisher=publisher,
        publish_time=publish_time,
        view_count=view_count,
        source_team=team_name,
        source_url=source_url,
    )


def fetch_post_detail(session: requests.Session, detail_url: str) -> dict:
    """获取帖子详情页内容。

    返回：
    - 包含 title, content, author, publish_time 等字段的字典
    """
    url = urljoin(TEAMWORK_BASE, detail_url)
    resp = session.get(url, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    detail: dict = {
        "url": url,
        "title": "",
        "content": "",
        "author": "",
        "publish_time": "",
        "attachments": [],
    }

    # 标题
    post_title_div = soup.find("div", id="postTitle")
    if post_title_div:
        detail["title"] = post_title_div.get_text(strip=True)

    # 发布者（团队名）
    team_div = soup.find("div", id="team_div")
    if team_div:
        detail["author"] = team_div.get_text(strip=True)

    # 发布日期
    post_icons = soup.find_all("div", class_="post-icon")
    if len(post_icons) >= 3:
        detail["publish_time"] = post_icons[2].get_text(strip=True)

    # 内容区域
    content_div = soup.find("div", id="objId")
    if content_div:
        detail["content"] = content_div.get_text(" ", strip=True)[:5000]

    # 附件
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if any(
            href.lower().endswith(ext)
            for ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar", ".ppt", ".pptx"]
        ):
            detail["attachments"].append(
                {"name": a.get_text(strip=True), "url": urljoin(TEAMWORK_BASE, href)}
            )

    return detail
