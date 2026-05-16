# 学者网数据工具集

自动登录[学者网](https://www.scholat.com)，抓取课程作业、栏目日程、团队帖子，
输出为结构化 JSON，供下游自行处理。

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 .env（只需学者网账号）
echo 'SCHOLAT_USERNAME=your_email@example.com' > .env
echo 'SCHOLAT_PASSWORD=your_password' >> .env

# 3. 运行
python fetch_homework.py --limit 5          # 课程作业
python fetch_general.py                     # 通用栏目日程
python fetch_teamwork.py --max-pages 1      # 团队帖子（7个预置团队）
```

---

## 文件结构

```
scholat/
├── README.md
├── requirements.txt              # Python 依赖
├── .env                          # 账号密码配置
│
├── fetch_homework.py             # [入口] 课程作业 → JSON
├── fetch_general.py              # [入口] 通用栏目日程 → JSON
├── fetch_teamwork.py             # [入口] 团队帖子 → JSON（含附件链接提取）
│
├── scholat_sync/                 # 核心逻辑包
│   ├── __init__.py
│   ├── config.py                 # 从 .env 加载所有配置
│   ├── auth.py                   # 学者网登录（DES 加密，需 Node.js）
│   ├── models.py                 # 数据模型定义
│   ├── homework.py               # 作业页 HTML 解析 + 截止时间提取 + 排序
│   ├── scraper.py                # 通用栏目抓取 + 日期正则识别
│   ├── teamwork.py               # 团队帖子抓取 + 分页遍历 + 详情 + 附件提取
│   └── feishu.py                 # 飞书 API 封装（token、日历、事件 CRUD）
│
└── tools/
    ├── setup_calendar.py         # 创建飞书日历 + 添加订阅者
    └── test_permissions.py       # 飞书 API 权限诊断
```

---

## 架构分层

```
┌──────────────────────────────────────┐
│  CLI 入口层 (fetch_*.py)             │
│  参数解析 → 登录 → 调用核心函数        │
│  暴露可导入的 fetch_*() 函数          │
├──────────────────────────────────────┤
│  核心逻辑层 (scholat_sync/)           │
│  auth.py     → 登录态管理             │
│  homework.py → 作业页解析             │
│  scraper.py  → 通用栏目解析           │
│  teamwork.py → 团队帖子解析           │
│  config.py   → 统一配置               │
│  models.py   → 数据结构定义           │
├──────────────────────────────────────┤
│  外部依赖                             │
│  requests + BeautifulSoup + Node.js   │
└──────────────────────────────────────┘
```

三个 `fetch_*.py` 各自暴露一个同名函数，接受已登录的 `requests.Session`，
返回纯 `dict`。下游可以 `import` 后接任何输出端（飞书、企微、数据库、前端）。

---

## 爬取范围

### 当前能爬取的内容

| 数据源 | 具体内容 | 对应脚本 |
|--------|---------|----------|
| 课程作业列表 | 作业标题、发布人、截止日期、提交状态、详情链接 | `fetch_homework.py` |
| 首页栏目日程 | 「我的动态」「我的课程」中含日期时间的条目（支持 `2026-04-11`、`4月11日 09:00`、`2026年4月11日` 等格式） | `fetch_general.py` |
| 团队协作平台帖子列表 | 帖子标题、发布时间、发布者、可见范围、浏览次数、详情链接（支持自动翻页） | `fetch_teamwork.py` |
| 团队帖子详情 | 正文全文、附件下载链接（`.pdf` `.doc` `.xls` `.ppt` 等文件 + 百度网盘、腾讯文档、WPS、金山文档等云盘链接）、正文中的外部链接 | `fetch_teamwork.py --detail` |
| 预置团队 | 计算机团委、计算机学生会、计算机党建中心、2022级、2023级、2024级、研究生（共 7 个） | `fetch_teamwork.py` |

### 当前不能爬取的内容

| 限制 | 说明 |
|------|------|
| 作业详情正文 | 仅抓取列表页的标题和截止时间，不进入每个作业的详情页 |
| 无日期文本的栏目条目 | 通用栏目仅提取含明确日期时间的文本，纯文字公告不抓取 |
| 帖子中的图片 | 详情正文中的 `<img>` 图片不提取 |
| 附件文件本体 | 附件只提供下载链接，不下载文件 |
| 团队分类筛选 | 不区分团队的「全部动态」「未分类动态」等子分类，全部抓取 |
| 学者网其他页面 | 不支持团队资源、成员列表、个人主页等页面 |

---

## 使用详解

### 一、课程作业 (`fetch_homework.py`)

```bash
# 基础用法
python fetch_homework.py                              # 全部有截止时间的作业
python fetch_homework.py --limit 5                    # 最近 5 条
python fetch_homework.py --all                        # 包含无截止时间的
python fetch_homework.py -o homework.json             # 输出到文件

# 指定课程
python fetch_homework.py --url "https://www.scholat.com/course/S_homeworkList.html?courseId=XXX"

# 紧凑输出
python fetch_homework.py --compact
```

输出示例：

```json
{
  "url": "https://www.scholat.com/course/S_homeworkList.html?courseId=100",
  "total": 6,
  "count": 3,
  "homeworks": [
    {
      "status": "按时提交",
      "title": "2023-osdev-lab1",
      "publisher": "李丁丁",
      "deadline_text": "2025-09-30 不可延时提交",
      "deadline_date": "2025-09-30 20:00",
      "detail_url": "https://www.scholat.com/course/S_oneHomework.html?..."
    }
  ]
}
```

**可导入函数：**

```python
from fetch_homework import fetch_homework

# session 已登录
data = fetch_homework(session, url="...", limit=10, include_no_deadline=False)
```

---

### 二、通用栏目日程 (`fetch_general.py`)

```bash
python fetch_general.py                              # 抓取全部栏目
python fetch_general.py --per-section-limit 10       # 每栏目最多 10 条
python fetch_general.py --section 我的动态           # 只抓取指定栏目
python fetch_general.py -o general.json
```

输出示例：

```json
{
  "sections": [
    {
      "name": "我的动态",
      "url": "https://www.scholat.com/showUnReadDynamicMessage.html",
      "count": 3,
      "items": [
        {
          "title": "学术报告通知",
          "source_section": "我的动态",
          "source_url": "https://...",
          "text": "2026年5月20日 14:00 学术报告...",
          "start_time": "2026-05-20 14:00",
          "end_time": "2026-05-20 15:00"
        }
      ]
    }
  ]
}
```

**可导入函数：**

```python
from fetch_general import fetch_general

data = fetch_general(session, per_section_limit=10, section_filter="我的动态")
```

---

### 三、团队帖子 (`fetch_teamwork.py`)

预置 7 个团队：

| 团队 | 团队 ID | nav |
|------|---------|-----|
| 计算机团委 | 671 | 3 |
| 计算机学生会 | 1253 | 3 |
| 计算机党建中心 | 2086 | 4 |
| 2022级 | 1473 | 4 |
| 2023级 | 1136 | 3 |
| 2024级 | 2157 | 4 |
| 研究生 | 1259 | 3 |

```bash
python fetch_teamwork.py                            # 抓取全部预置团队
python fetch_teamwork.py --team 团委                # 模糊匹配单个
python fetch_teamwork.py --id 671 --nav 3           # 按 ID 抓取
python fetch_teamwork.py --max-pages 2              # 限制页数
python fetch_teamwork.py --detail                   # 含附件链接和正文
python fetch_teamwork.py --detail -o posts.json     # 输出到文件
```

输出示例（`--detail` 模式）：

```json
{
  "teams": [
    {
      "name": "计算机团委",
      "id": 671,
      "nav": 3,
      "post_count": 10,
      "posts": [
        {
          "index": 1,
          "title": "【评比公示】2024年暑期社会三下乡...",
          "detail_url": "https://www.scholat.com/teamwork/showPostMessage.html?id=15537",
          "visibility": "公开信息",
          "publisher": "管理员",
          "publish_time": "2024-04-27",
          "view_count": 4821,
          "source_team": "SCNU-CS 团团君",
          "source_url": "https://www.scholat.com/showTeamworkPostMessage.html?...",
          "detail": {
            "url": "https://www.scholat.com/teamwork/showPostMessage.html?id=15537",
            "title": "【评比公示】2024年暑期社会三下乡...",
            "content": "全院师生：根据校团委下发的...",
            "author": "SCNU-CS 团团君",
            "publish_time": "2024-04-27",
            "attachments": [
              {"name": "附件1.doc", "url": "http://statics.scnu.edu.cn/..."}
            ],
            "links": [
              {"name": "通知公告", "url": "http://xsb.scnu.edu.cn/..."}
            ]
          }
        }
      ]
    }
  ]
}
```

**可导入函数：**

```python
from fetch_teamwork import fetch_teamwork, PRESET_TEAMS

data = fetch_teamwork(session, teams=[("团委", PRESET_TEAMS["计算机团委"])],
                      max_pages=2, with_detail=True)
# data["teams"][0]["posts"][0]["detail"]["attachments"]  → 附件链接列表
# data["teams"][0]["posts"][0]["detail"]["links"]        → 外部链接列表
```

---

## .env 配置说明

```ini
# ==== 学者网账号（必填） ====
SCHOLAT_USERNAME=your_email@example.com
SCHOLAT_PASSWORD=your_password

# ==== 可选配置 ====
SCHOLAT_LOGIN_URL=https://www.scholat.com/login.html
SCHOLAT_HOME_URL=https://www.scholat.com/Phomepage.html
TIMEZONE=Asia/Shanghai

# ==== 作业页 URL（可选，fetch_homework.py 默认值） ====
SCHOLAT_HOMEWORK_TEST_URL=https://www.scholat.com/course/S_homeworkList.html?courseId=100

# ==== 飞书应用凭证（仅 tools/setup_calendar.py 和 test_permissions.py 需要） ====
APP_ID=cli_xxxxxxxxxxxxxx
APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxx
CALENDAR_ID=xxxxxxxxxx@group.calendar.feishu.cn
EMAIL=your_email@example.com
PHONE=138xxxxxxxx
```

---

## 接口速查表

| 函数 | 来源文件 | 返回结构 |
|------|----------|----------|
| `fetch_homework(session, url?, limit, include_no_deadline)` | `fetch_homework.py` | `{url, total, count, homeworks: [...]}` |
| `fetch_general(session, home_url?, per_section_limit, section_filter?)` | `fetch_general.py` | `{sections: [{name, url, count, items: [...]}]}` |
| `fetch_teamwork(session, teams, max_pages?, with_detail?)` | `fetch_teamwork.py` | `{teams: [{name, id, nav, post_count, posts: [...]}]}` |

所有函数均接受已登录的 `requests.Session`，返回纯 `dict`，无副作用。

---

## 依赖

**系统依赖：**

- Python 3.11+
- Node.js（学者网密码加密需要，`node` 命令需在 PATH 中）

**Python 依赖（`pip install -r requirements.txt`）：**

- `requests>=2.28`
- `beautifulsoup4>=4.12`
- `python-dotenv>=1.0`

