"""学者网通用栏目抓取接口（纯数据流出，可导入复用）。

提供可导入的 fetch_general() 函数，返回栏目日程列表 dict，
可自行处理数据（输出 JSON、接入飞书等）。

CLI 用法：
    python fetch_general.py                                # 抓取全部栏目
    python fetch_general.py --per-section-limit 10         # 每栏目最多 10 条
    python fetch_general.py --section 我的动态             # 只抓取指定栏目
    python fetch_general.py --output general.json          # 输出到文件


依赖：pip install requests beautifulsoup4 python-dotenv（另需系统安装 Node.js）
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Optional

import requests

from scholat_sync.auth import login_scholat
from scholat_sync.config import SCHOLAT_HOME_URL
from scholat_sync.scraper import extract_section_links, scrape_schedule_items


def fetch_general(
    session: requests.Session,
    home_url: Optional[str] = None,
    per_section_limit: int = 20,
    section_filter: Optional[str] = None,
) -> dict:
    """抓取学者网首页通用栏目日程。

    参数：
    - session: 已登录的 requests.Session
    - home_url: 学者网首页 URL，默认使用 .env 配置
    - per_section_limit: 每个栏目最多抓取条数
    - section_filter: 栏目名模糊匹配，None=全部

    返回：
    {
        "sections": [
            {
                "name": str,
                "url": str,
                "count": int,
                "items": [
                    {
                        "title": str,
                        "source_section": str,
                        "source_url": str,
                        "text": str,
                        "start_time": str,
                        "end_time": str,
                    }
                ]
            }
        ]
    }
    """
    if home_url is None:
        home_url = SCHOLAT_HOME_URL

    home_resp = session.get(home_url, timeout=30)
    home_resp.raise_for_status()

    section_links = extract_section_links(home_resp.text)
    if not section_links:
        section_links = [("首页", home_url)]

    if section_filter:
        section_links = [(s, u) for s, u in section_links if section_filter in s]

    sections: list[dict] = []

    for section, url in section_links:
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            items = scrape_schedule_items(section, url, resp.text, per_section_limit)

            sections.append(
                {
                    "name": section,
                    "url": url,
                    "count": len(items),
                    "items": [
                        {
                            "title": item.title,
                            "source_section": item.source_section,
                            "source_url": item.source_url,
                            "text": item.text,
                            "start_time": item.start_dt.strftime("%Y-%m-%d %H:%M"),
                            "end_time": item.end_dt.strftime("%Y-%m-%d %H:%M"),
                        }
                        for item in items
                    ],
                }
            )
        except Exception:
            pass  # 单个栏目抓取失败不阻断整体

    return {"sections": sections}


def _create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        }
    )
    return session


def main() -> None:
    parser = argparse.ArgumentParser(description="抓取学者网通用栏目日程")
    parser.add_argument(
        "--per-section-limit", type=int, default=20, help="每栏目最多条数"
    )
    parser.add_argument("--section", type=str, help="只抓取指定栏目（模糊匹配）")
    parser.add_argument(
        "--output", "-o", type=str, help="输出 JSON 文件路径，默认 stdout"
    )
    parser.add_argument("--compact", action="store_true", help="紧凑 JSON 输出")
    args = parser.parse_args()

    session = _create_session()

    print("[INFO] 登录学者网...", file=sys.stderr)
    login_scholat(session)
    print("[INFO] 登录成功", file=sys.stderr)

    result = fetch_general(
        session,
        per_section_limit=args.per_section_limit,
        section_filter=args.section,
    )

    total = sum(s["count"] for s in result["sections"])
    print(
        f"[INFO] 抓取 {len(result['sections'])} 个栏目，共 {total} 条", file=sys.stderr
    )

    indent = None if args.compact else 2
    json_str = json.dumps(result, ensure_ascii=False, indent=indent)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"[INFO] 已写入 {args.output}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == "__main__":
    main()
