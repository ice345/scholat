# 学者网数据工具集

自动登录[学者网](https://www.scholat.com)，支持模式：

- **流出模式** — 抓取数据后输出 JSON，供下游自行处理（`fetch_*.py`）

覆盖三类数据源：课程作业、通用栏目日程、团队协作平台帖子。

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 .env（见下方说明）

# 3. 数据流出（不需要飞书，纯 JSON 输出）
python fetch_homework.py --limit 5
python fetch_teamwork.py --max-pages 1

```

---

## 文件结构

```
scholat/
├── README.md
├── requirements.txt
├── .env
│
├── fetch_homework.py             # [数据流出] 作业 → JSON
├── fetch_general.py              # [数据流出] 通用栏目 → JSON
├── fetch_teamwork.py             # [数据流出] 团队帖子 → JSON
│
├── scholat_sync/                 # 核心逻辑包
│   ├── __init__.py
│   ├── config.py                 # 配置加载（.env）
│   ├── auth.py                   # 学者网登录（DES 加密）
│   ├── feishu.py                 # 飞书 API 封装
│   ├── models.py                 # 数据模型（ScheduleItem, HomeworkItem, TeamworkPost）
│   ├── homework.py               # 作业页解析 + 排序 + 去重
│   ├── scraper.py                # 通用栏目抓取 + 日期识别 + 去重
│   └── teamwork.py               # 团队协作平台抓取 + 分页 + 详情
│
└── tools/
    ├── setup_calendar.py         # [一次性] 创建飞书日历 + 添加订阅者
    └── test_permissions.py       # [排障] 飞书 API 权限测试
```

---

## .env 配置说明

```ini
# ---- 飞书应用凭证（同步模式必填，纯流出模式可省略） ----
APP_ID=cli_xxxxxxxxxxxxxx
APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxx
CALENDAR_ID=xxxxxxxxxx@group.calendar.feishu.cn

# ---- 学者网账号（必填） ----
SCHOLAT_USERNAME=your_email@example.com
SCHOLAT_PASSWORD=your_password

# ---- 飞书用户信息（订阅用） ----
EMAIL=your_email@example.com
PHONE=138xxxxxxxx

# ---- 可选参数 ----
TIMEZONE=Asia/Shanghai
SCHOLAT_HOMEWORK_TEST_URL=https://www.scholat.com/course/S_homeworkList.html?courseId=100
```
```ini
APP_ID=
APP_SECRET=
CALENDAR_ID=
PHONE=
EMAIL=

SCHOLAT_USERNAME=
SCHOLAT_PASSWORD=
SCHOLAT_LOGIN_URL=
SCHOLAT_HOME_URL=
SYNC_CALENDAR_NAME=
SYNC_CALENDAR_DESC=
SYNC_STATE_FILE=
TIMEZONE=

SCHOLAT_HOMEWORK_TEST_URL=
HOMEWORK_TEST_CALENDAR_ID=
HOMEWORK_TEST_CALENDAR_NAME=学者网作业测试
```

---

## 使用场景

### 场景一：数据流出

三个 `fetch_*.py` 均可通过 CLI 直接使用，也支持 `import` 复用。

#### 课程作业

```bash
python fetch_homework.py --limit 5
python fetch_homework.py --url "https://www.scholat.com/course/S_homeworkList.html?courseId=XXX" --limit 10
python fetch_homework.py --all                    # 包含无截止时间的作业
python fetch_homework.py -o homework.json
```

#### 通用栏目日程

```bash
python fetch_general.py --per-section-limit 10
python fetch_general.py --section 我的动态
python fetch_general.py -o general.json
```

#### 团队协作平台帖子

预置团队：计算机团委(id=671)、计算机学生会(id=1253)、计算机党建中心(id=2086)、
2022级(id=1473)、2023级(id=1136)、2024级(id=2157)、研究生(id=1259)

```bash
python fetch_teamwork.py                          # 抓取全部预置团队
python fetch_teamwork.py --team 团委              # 模糊匹配单个团队
python fetch_teamwork.py --id 671 --nav 3         # 按 ID 抓取
python fetch_teamwork.py --max-pages 2            # 限制页数
python fetch_teamwork.py --detail                 # 同时抓取帖子详情
python fetch_teamwork.py -o posts.json
```

#### 代码复用（import）

```python
from scholat_sync.auth import login_scholat
from fetch_homework import fetch_homework
from fetch_general import fetch_general
from fetch_teamwork import fetch_teamwork, PRESET_TEAMS

# 登录后即可调用，自行处理返回的 dict
login_scholat(session)

data = fetch_homework(session, url="...", limit=10)
data = fetch_general(session, per_section_limit=10, section_filter="我的动态")
data = fetch_teamwork(session, teams=[("团委", PRESET_TEAMS["计算机团委"])])

# data 是 dict，可以接入飞书
```


### 场景二：首次初始化飞书

```bash
python tools/setup_calendar.py
# → 输出 calendar_id，将其填入 .env 的 CALENDAR_ID
```

### 场景三：排障 / 验证飞书权限

```bash
python tools/test_permissions.py
```

