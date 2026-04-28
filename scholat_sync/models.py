"""数据模型定义。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ScheduleItem:
    """通用日程数据模型。

    字段：
    - title: 事件标题。
    - source_section: 来源栏目名称。
    - source_url: 来源页面或详情链接。
    - text: 原始文本内容。
    - start_dt: 事件开始时间。
    - end_dt: 事件结束时间。
    """

    title: str
    source_section: str
    source_url: str
    text: str
    start_dt: datetime
    end_dt: datetime


@dataclass
class HomeworkItem:
    """作业条目数据模型。"""

    status: str
    title: str
    publisher: str
    deadline_text: str
    deadline_date: Optional[datetime]
    detail_url: str
