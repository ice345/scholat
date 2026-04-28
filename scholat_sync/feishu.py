"""飞书 Open API 统一封装。"""

import json
import time
from typing import Any, Optional

import requests

from .config import APP_ID, APP_SECRET, FEISHU_CALENDAR_ID, SYNC_CALENDAR_DESC, SYNC_CALENDAR_NAME, TIMEZONE


def get_tenant_access_token() -> str:
    """获取飞书 tenant_access_token。"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    token = data.get("tenant_access_token")
    if not token:
        raise RuntimeError(f"获取 tenant_access_token 失败: {data}")
    return token


def feishu_request(
    method: str,
    url: str,
    token: str,
    payload: Optional[dict] = None,
    params: Optional[dict] = None,
) -> dict:
    """统一封装飞书 API 请求。"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    response = requests.request(
        method,
        url,
        headers=headers,
        data=json.dumps(payload) if payload is not None else None,
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def ensure_calendar(token: str) -> str:
    """确保可用目标日历。

    若已配置 CALENDAR_ID 则直接使用，否则自动创建私有日历。
    """
    if FEISHU_CALENDAR_ID:
        return FEISHU_CALENDAR_ID

    url = "https://open.feishu.cn/open-apis/calendar/v4/calendars"
    payload = {
        "summary": SYNC_CALENDAR_NAME,
        "description": SYNC_CALENDAR_DESC,
        "permissions": "private",
    }
    data = feishu_request("POST", url, token, payload=payload)
    if data.get("code") != 0:
        raise RuntimeError(f"创建飞书日历失败: {data}")

    calendar_id = data["data"]["calendar"]["calendar_id"]
    print(f"[INFO] 已自动创建日历，CALENDAR_ID={calendar_id}")
    return calendar_id


def create_event(token: str, calendar_id: str, summary: str, description: str,
                  start_ts: int, end_ts: int) -> dict:
    """在指定日历中创建事件。"""
    url = f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/events"
    payload = {
        "summary": summary,
        "description": description,
        "start_time": {"timestamp": str(start_ts), "timezone": TIMEZONE},
        "end_time": {"timestamp": str(end_ts), "timezone": TIMEZONE},
    }
    data = feishu_request("POST", url, token=token, payload=payload)
    if data.get("code") != 0:
        raise RuntimeError(f"创建飞书事件失败: {data}")
    return data


def get_user_open_id(token: str, email: str, phone: str) -> Optional[str]:
    """通过 EMAIL（优先）/ PHONE（回退）查询飞书用户 open_id。"""
    url = "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id"

    if email:
        _, data = feishu_request(
            "POST", url, token=token,
            payload={"emails": [email]},
            params={"user_id_type": "open_id"},
        )
        user_list = data.get("data", {}).get("user_list", [])
        if user_list and user_list[0].get("user_id"):
            return user_list[0]["user_id"]

    if phone:
        _, data = feishu_request(
            "POST", url, token=token,
            payload={"mobiles": [phone]},
            params={"user_id_type": "open_id"},
        )
        user_list = data.get("data", {}).get("user_list", [])
        if user_list and user_list[0].get("user_id"):
            return user_list[0]["user_id"]

    return None


def create_calendar(token: str, name: str, description: str) -> str:
    """创建飞书日历，返回 calendar_id。"""
    url = "https://open.feishu.cn/open-apis/calendar/v4/calendars"
    payload = {
        "summary": name,
        "description": description,
        "permissions": "private",
    }
    data = feishu_request("POST", url, token=token, payload=payload)
    if data.get("code") != 0:
        raise RuntimeError(f"创建飞书日历失败: {data.get('msg')}")
    return data["data"]["calendar"]["calendar_id"]


def add_calendar_subscriber(token: str, calendar_id: str, open_id: str, role: str = "writer") -> dict:
    """将用户添加为日历订阅者。"""
    url = f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/acls"
    payload = {
        "role": role,
        "scope": {"type": "user", "user_id": open_id},
    }
    data = feishu_request("POST", url, token=token, payload=payload, params={"user_id_type": "open_id"})
    return data


def remove_calendar_subscriber(token: str, calendar_id: str, acl_id: str) -> dict:
    """移除日历订阅者。"""
    url = f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/acls/{acl_id}"
    data = feishu_request("DELETE", url, token=token)
    return data


def delete_event(token: str, calendar_id: str, event_id: str) -> dict:
    """删除日历事件。"""
    url = f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/events/{event_id}"
    data = feishu_request("DELETE", url, token=token)
    return data


def delete_calendar(token: str, calendar_id: str) -> dict:
    """删除日历。"""
    url = f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}"
    data = feishu_request("DELETE", url, token=token)
    return data


def get_calendar(token: str, calendar_id: str) -> dict:
    """获取日历信息。"""
    url = f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}"
    return feishu_request("GET", url, token=token)


def update_calendar(token: str, calendar_id: str, payload: dict) -> dict:
    """更新日历信息。"""
    url = f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}"
    return feishu_request("PATCH", url, token=token, payload=payload)


def get_event(token: str, calendar_id: str, event_id: str) -> dict:
    """获取事件详情。"""
    url = f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/events/{event_id}"
    return feishu_request("GET", url, token=token)


def update_event(token: str, calendar_id: str, event_id: str, payload: dict) -> dict:
    """更新事件。"""
    url = f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/events/{event_id}"
    return feishu_request("PATCH", url, token=token, payload=payload)


def list_events(token: str, calendar_id: str, page_size: int = 50) -> list[dict]:
    """列出日历中的事件。

    返回事件列表（每个事件为一个 dict，包含 event_id, summary 等）。
    """
    url = f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/events"
    data = feishu_request("GET", url, token=token, params={"page_size": str(page_size)})
    if data.get("code") != 0:
        raise RuntimeError(f"获取事件列表失败: {data}")
    return data.get("data", {}).get("items", [])
