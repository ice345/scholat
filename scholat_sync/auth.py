"""学者网自动登录模块。"""

import re
import subprocess
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .config import SCHOLAT_LOGIN_URL, SCHOLAT_PASSWORD, SCHOLAT_USERNAME


def parse_login_page(login_html: str) -> tuple[str, str]:
    """解析登录页，提取密码加密所需参数。

    返回：
    - session_value
    - login.gzjs 脚本地址
    """
    match_session = re.search(r'var\s+session_value\s*=\s*"([A-Fa-f0-9]+)"', login_html)
    if not match_session:
        raise RuntimeError("未在登录页找到 session_value，无法加密密码")
    session_value = match_session.group(1)

    soup = BeautifulSoup(login_html, "html.parser")
    script_src = None
    for script in soup.find_all("script"):
        src = script.get("src")
        if src and "login.gzjs" in src:
            script_src = src
            break

    if not script_src:
        raise RuntimeError("未在登录页找到 login.gzjs 脚本")
    return session_value, script_src


def encrypt_password(password: str, login_js_text: str, session_value: str) -> str:
    """调用学者网前端加密函数 strEnc 生成加密密码。"""
    import json

    pw_json = json.dumps(password)
    sv_json = json.dumps(session_value)
    script = (
        login_js_text
        + f"\nconsole.log(strEnc({pw_json}, {sv_json}, 'userc', 'pfir'));"
    )
    result = subprocess.run(
        ["node", "--eval", script],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Node.js 执行加密脚本失败：{result.stderr.strip()}")
    return result.stdout.strip()


def login_scholat(session: requests.Session) -> None:
    """执行学者网登录并在 session 中保留登录态。"""
    if not SCHOLAT_USERNAME or not SCHOLAT_PASSWORD:
        raise RuntimeError("请在 .env 配置 SCHOLAT_USERNAME 和 SCHOLAT_PASSWORD")

    login_resp = session.get(SCHOLAT_LOGIN_URL, timeout=30)
    login_resp.raise_for_status()
    login_html = login_resp.text

    session_value, script_src = parse_login_page(login_html)
    script_url = urljoin(SCHOLAT_LOGIN_URL, script_src)
    login_js_text = session.get(script_url, timeout=30).text
    encrypted = encrypt_password(SCHOLAT_PASSWORD, login_js_text, session_value)

    soup = BeautifulSoup(login_html, "html.parser")
    form = soup.find("form")
    if not form:
        raise RuntimeError("未找到登录表单")

    action = form.get("action", "Auth.html")
    auth_url = urljoin(SCHOLAT_LOGIN_URL, action)
    payload = {
        "j_username": SCHOLAT_USERNAME,
        "j_password_ext": SCHOLAT_PASSWORD,
        "j_passdec": encrypted,
        "j_service": "",
        "urlBeforeLogin": "",
    }

    auth_resp = session.post(auth_url, data=payload, timeout=30, allow_redirects=True)
    auth_resp.raise_for_status()

    if "wrong username or password" in auth_resp.text.lower() or "用户名与密码不匹配" in auth_resp.text:
        raise RuntimeError("学者网登录失败：用户名或密码错误")

    if "login" in auth_resp.url and "scholat.com/login" in auth_resp.url:
        raise RuntimeError("学者网登录可能失败，仍停留在登录页")
