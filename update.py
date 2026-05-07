"""
Gamer520 每日PC游戏更新 - GitHub Actions 版
从网站抓取当天游戏 → 生成HTML → 推送到GitHub → Cloudflare/Vercel自动部署
"""
import requests
import json
import re
import base64
import os
from datetime import datetime
from bs4 import BeautifulSoup

# ========== 配置 ==========
SITE_URL = "https://www.gamer520.com/pcplay"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "ilan3437/gamer520-daily")
GITHUB_API = "https://api.github.com"

# 飞书配置（从环境变量读取）
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_API = "https://open.feishu.cn/open-apis"

# 网页地址
CLOUDFLARE_URL = "https://gamer520-daily.pages.dev"

# ========== 类型推断 ==========
TYPE_RULES = [
    (['战记', '战争', '三国', '战国'], '策略/战棋'),
    (['模拟器', '天际线', '加油站', '经销商', '驿站', '挖矿', '创业', '农庄', '卡车'], '模拟/经营'),
    (['RPG', '英雄无敌', '武侠', '明末', '英雄传', '大宋'], '角色扮演'),
    (['生存', '深空', '感染', '劫后'], '生存/冒险'),
    (['格斗', '无双', '战斗之潮', '电锯姬', '圣杯'], '动作/格斗'),
    (['卡牌', '牌', '恶魔牌', '弈战'], '卡牌/策略'),
    (['自走棋', '团本'], '策略/自走棋'),
    (['恋爱', '物语', '天使'], '视觉小说'),
    (['塔防', '炮塔'], '策略/塔防'),
    (['摸鱼', '放置'], '放置/模拟'),
    (['云族裔', 'inZOI'], '模拟/生活'),
    (['最终幻想', 'FF'], 'JRPG/动作'),
    (['开拓者', '正义之怒'], 'RPG/策略'),
    (['推币机', '火柴人'], '休闲/模拟'),
    (['迪斯科'], '节奏/格斗'),
    (['跑酷'], '跑酷/动作'),
]

def get_game_type(name):
    for keywords, gtype in TYPE_RULES:
        for kw in keywords:
            if kw in name:
                return gtype
    return '动作/冒险'

def get_proxy_image_url(url):
    """使用图片代理解决国内访问问题"""
    if not url:
        return ''
    # 使用 wsrv.nl 代理服务
    if url.startswith('http'):
        # 编码URL
        encoded = url.replace('https://', '').replace('http://', '')
        return f"https://wsrv.nl/?url={encoded}&w=160&h=90&fit=cover"
    return url

# ========== 抓取游戏 ==========
def fetch_games():
    """抓取当天更新的游戏（只抓取页面底部的统一时间在24小时内的）"""
    games = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    for page in range(1, 6):
        url = f"{SITE_URL}/page/{page}" if page > 1 else SITE_URL
        try:
            resp = requests.get(url, timeout=15, headers=headers)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')

            articles = soup.find_all('article')

            # 获取页面底部的统一更新时间
            page_time = ''
            nav = soup.find('nav', class_='pagination') or soup.find('div', class_='nav-links')
            if nav:
                prev_text = nav.find_previous_sibling(string=True)
                if prev_text:
                    time_match = re.search(r'(\d+小时前|\d+天前|昨天)', prev_text)
                    if time_match:
                        page_time = time_match.group(1)

            # 如果没找到，从页面文本中找
            if not page_time:
                page_text = soup.get_text()
                time_matches = re.findall(r'(\d+小时前|\d+天前|昨天)', page_text)
                if time_matches:
                    page_time = time_matches[-1]

            # 如果页面时间超过24小时，停止翻页
            if page_time:
                hour_match = re.search(r'(\d+)小时前', page_time)
                if hour_match:
                    hours = int(hour_match.group(1))
                    if hours > 24:
                        print(f"  第{page}页更新于{page_time}，超过24小时，停止翻页")
                        break
                day_match = re.search(r'(\d+)天前', page_time)
                if day_match:
                    days = int(day_match.group(1))
                    if days >= 1:
                        print(f"  第{page}页更新于{page_time}，超过24小时，停止翻页")
                        break

            for article in articles:
                try:
                    h2 = article.find('h2', class_='entry-title')
                    if not h2:
                        continue

                    link_tag = h2.find('a', href=True)
                    if not link_tag:
                        continue

                    link = link_tag['href']
                    if not link or '.html' not in link:
                        continue

                    if 'gamer520.com' not in link:
                        link = 'https://www.gamer520.com' + link

                    title = link_tag.get_text(strip=True)
                    if not title or '解压即撸' not in title:
                        continue

                    name = title.split('|')[0].strip()

                    # 获取封面图并使用代理
                    cover = ''
                    img = article.find('img')
                    if img:
                        raw_cover = img.get('src', '') or img.get('data-src', '') or img.get('data-original', '')
                        cover = get_proxy_image_url(raw_cover)

                    game_type = get_game_type(name)

                    games.append({
                        'name': name,
                        'type': game_type,
                        'time': page_time if page_time else '',
                        'cover': cover,
                        'link': link
                    })

                except Exception:
                    continue

        except Exception as e:
            print(f"  抓取第{page}页失败: {e}")
            continue

    # 去重
    seen = set()
    unique = []
    for g in games:
        if g['name'] not in seen:
            seen.add(g['name'])
            unique.append(g)

    # 按时间排序：最新的放前面（小时数越小越新，所以用负数排序）
    def sort_key(g):
        t = g['time']
        # 提取小时数，数字越小越新，用负数实现倒序
        m = re.search(r'(\d+)', t)
        if m:
            return -int(m.group(1))  # 负数，让小的排前面
        return -999
    unique.sort(key=sort_key)

    return unique

# ========== 生成HTML ==========
def generate_html(games, date_str, update_time):
    """生成游戏列表HTML"""

    games_json = json.dumps(games, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>Gamer520 PC游戏更新 - {date_str}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;900&display=swap');
:root {{
    --bg: #0a0a0f;
    --card: #14141f;
    --card-hover: #1a1a2e;
    --border: #2a2a3e;
    --accent: #00e68a;
    --text: #e8e8f0;
    --text-dim: #8888a0;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 20px 16px;
    max-width: 600px;
    margin: 0 auto;
    min-height: 100vh;
}}
.header {{
    text-align: center;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
}}
.header h1 {{
    font-size: 22px;
    font-weight: 900;
    background: linear-gradient(135deg, #00e68a, #00b8ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.header .date {{
    font-size: 13px;
    color: var(--text-dim);
    margin-top: 4px;
}}
.header .count {{
    font-size: 12px;
    color: var(--accent);
    background: rgba(0,230,138,0.1);
    padding: 4px 12px;
    border-radius: 20px;
    display: inline-block;
    margin-top: 8px;
}}
.refresh-btn {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: linear-gradient(135deg, var(--accent), #00b8ff);
    color: #000;
    border: none;
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    margin-top: 12px;
    transition: all 0.2s ease;
}}
.refresh-btn:hover {{
    transform: scale(1.05);
}}
.refresh-btn:active {{
    transform: scale(0.98);
}}
.refresh-btn.loading {{
    opacity: 0.7;
    pointer-events: none;
}}
.refresh-btn .spinner {{
    display: none;
    width: 14px;
    height: 14px;
    border: 2px solid #000;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}}
.refresh-btn.loading .spinner {{
    display: inline-block;
}}
@keyframes spin {{
    to {{ transform: rotate(360deg); }}
}}
.game-card {{
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 10px;
    margin-bottom: 8px;
    text-decoration: none;
    color: inherit;
    transition: all 0.2s ease;
    animation: fadeIn 0.4s ease backwards;
}}
@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
.game-cover-wrapper {{
    width: 80px;
    height: 45px;
    border-radius: 6px;
    flex-shrink: 0;
    background: linear-gradient(135deg, #1e1e30, #2a2a3e);
    overflow: hidden;
    position: relative;
}}
.game-cover {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    cursor: zoom-in;
}}
.game-cover-placeholder {{
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    background: linear-gradient(135deg, #1e1e30, #2a2a3e);
}}
.game-info {{
    flex: 1;
    min-width: 0;
}}
.game-name {{
    font-size: 14px;
    font-weight: 700;
    line-height: 1.3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 4px;
}}
.game-meta {{
    display: flex;
    align-items: center;
    gap: 6px;
}}
.game-tag {{
    font-size: 11px;
    color: var(--accent);
    background: rgba(0,230,138,0.1);
    border: 1px solid rgba(0,230,138,0.25);
    padding: 1px 6px;
    border-radius: 4px;
}}
.game-time {{
    font-size: 11px;
    color: var(--text-dim);
}}
.footer {{
    text-align: center;
    padding: 16px;
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 8px;
}}
.footer a {{
    color: var(--accent);
    text-decoration: none;
}}
.lightbox {{
    display: none;
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0,0,0,0.95);
    z-index: 1000;
    justify-content: center;
    align-items: center;
    padding: 20px;
}}
.lightbox.active {{
    display: flex;
}}
.lightbox img {{
    max-width: 100%;
    max-height: 80vh;
    border-radius: 8px;
}}
.lightbox-close {{
    position: absolute;
    top: 20px; right: 20px;
    width: 40px; height: 40px;
    background: rgba(255,255,255,0.1);
    border: none;
    border-radius: 50%;
    color: #fff;
    font-size: 24px;
    cursor: pointer;
}}
.toast {{
    position: fixed;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--card);
    border: 1px solid var(--border);
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 13px;
    z-index: 1001;
    opacity: 0;
    transition: opacity 0.3s ease;
}}
.toast.show {{
    opacity: 1;
}}
</style>
</head>
<body>
<div class="header">
    <h1>🎮 Gamer520 PC游戏更新</h1>
    <div class="date">{date_str}</div>
    <span class="count" id="count">共 {len(games)} 款</span>
    <br>
    <button class="refresh-btn" id="refreshBtn" onclick="handleRefresh()">
        <span class="spinner"></span>
        <span class="btn-text">🔄 刷新数据</span>
    </button>
</div>
<div class="list" id="gameList"></div>
<div class="footer">
    <span id="updateTime">更新时间: {update_time}</span> | <a href="{SITE_URL}" target="_blank">访问原网站</a>
</div>

<div class="lightbox" id="lightbox" onclick="closeLightbox()">
    <button class="lightbox-close" onclick="event.stopPropagation();closeLightbox()">&times;</button>
    <img id="lightboxImg" src="" alt="">
</div>

<div class="toast" id="toast"></div>

<script>
let GAMES_DATA = {games_json};
const GITHUB_RAW = "https://raw.githubusercontent.com/{GITHUB_REPO}/main/index.html";

function renderGames(games) {{
    const listEl = document.getElementById('gameList');
    const countEl = document.getElementById('count');
    if (!games || games.length === 0) {{
        listEl.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-dim)">今天暂无新游戏</div>';
        countEl.textContent = '共 0 款';
        return;
    }}
    countEl.textContent = `共 ${{games.length}} 款`;
    listEl.innerHTML = games.map((game, i) => `
        <a class="game-card" href="${{game.link}}" target="_blank" style="animation-delay:${{i*0.03}}s">
            <div class="game-cover-wrapper">
                <img class="game-cover" src="${{game.cover}}" alt="" loading="lazy"
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';"
                     onload="this.style.display='block'; this.nextElementSibling.style.display='none';"
                     onclick="event.preventDefault(); openLightbox('${{game.cover}}')">
                <div class="game-cover-placeholder">🎮</div>
            </div>
            <div class="game-info">
                <div class="game-name">${{i+1}}. ${{game.name}}</div>
                <div class="game-meta">
                    <span class="game-tag">${{game.type}}</span>
                    <span class="game-time">${{game.time}}</span>
                </div>
            </div>
        </a>
    `).join('');
}}

function openLightbox(src) {{
    if (!src) return;
    document.getElementById('lightboxImg').src = src;
    document.getElementById('lightbox').classList.add('active');
    document.body.style.overflow = 'hidden';
}}

function closeLightbox() {{
    document.getElementById('lightbox').classList.remove('active');
    document.body.style.overflow = '';
}}

function showToast(msg) {{
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}}

async function handleRefresh() {{
    const btn = document.getElementById('refreshBtn');
    btn.classList.add('loading');
    try {{
        const resp = await fetch(GITHUB_RAW + '?t=' + Date.now());
        if (!resp.ok) throw new Error('fail');
        const html = await resp.text();
        const m = html.match(/let GAMES_DATA = (\[[\s\S]*?\]);/);
        if (m) {{
            GAMES_DATA = JSON.parse(m[1]);
            renderGames(GAMES_DATA);
            showToast('已刷新，共 ' + GAMES_DATA.length + ' 款');
        }} else {{
            showToast('未找到数据');
        }}
    }} catch(e) {{
        showToast('刷新失败');
    }} finally {{
        btn.classList.remove('loading');
    }}
}}

document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeLightbox(); }});
renderGames(GAMES_DATA);
</script>
</body>
</html>'''
    return html

# ========== GitHub操作 ==========
def push_to_github(content, filename="index.html", message="Update"):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    get_resp = requests.get(url, headers=headers)
    sha = None
    if get_resp.status_code == 200:
        sha = get_resp.json().get("sha")

    data = {
        "message": message,
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        "branch": "main"
    }
    if sha:
        data["sha"] = sha

    resp = requests.put(url, headers=headers, json=data)
    if resp.status_code in [200, 201]:
        print(f"✅ 推送成功: {filename}")
        return True
    else:
        print(f"❌ 推送失败: {resp.json()}")
        return False

# ========== 飞书推送 ==========
def get_feishu_token():
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        return None
    url = f"{FEISHU_API}/auth/v3/app_access_token/internal"
    resp = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET})
    result = resp.json()
    return result.get("app_access_token") if result.get("code") == 0 else None

def send_feishu_card(token, date_str, game_count):
    if not token:
        return
    chats_resp = requests.get(f"{FEISHU_API}/im/v1/chats", headers={"Authorization": f"Bearer {token}"})
    chats = chats_resp.json().get("data", {}).get("items", [])
    if not chats:
        return

    for chat in chats:
        chat_id = chat.get("chat_id")
        chat_name = chat.get("name", "未知")

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"🎮 Gamer520 今日更新 ({date_str})"},
                "template": "green"
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": f"**{game_count}** 款新游戏已更新"}},
                {"tag": "action", "actions": [
                    {"tag": "button", "text": {"tag": "plain_text", "content": "📱 查看游戏列表"}, "type": "primary", "url": CLOUDFLARE_URL}
                ]},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": "每小时自动更新 | 点击封面可放大"}]}
            ]
        }

        resp = requests.post(
            f"{FEISHU_API}/im/v1/messages",
            params={"receive_id_type": "chat_id"},
            headers={"Authorization": f"Bearer {token}"},
            json={"receive_id": chat_id, "msg_type": "interactive", "content": json.dumps(card)}
        )
        result = resp.json()
        if result.get("code") == 0:
            print(f"✅ 飞书已发送到「{chat_name}」")
        else:
            print(f"❌ 飞书发送失败: {result.get('msg')}")

# ========== 主函数 ==========
if __name__ == "__main__":
    import sys
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    update_time = now.strftime('%H:%M')
    
    # 支持命令行参数 --feishu 强制推送
    force_feishu = '--feishu' in sys.argv
    send_feishu = force_feishu or os.environ.get("SEND_FEISHU", "false").lower() == "true"

    print(f"=== Gamer520 更新 ({date_str} {update_time}) ===")

    print("[1/3] 抓取游戏...")
    games = fetch_games()
    print(f"  抓取到 {len(games)} 款游戏")

    if not games:
        print("  没有新游戏，跳过")
        exit(0)

    for g in games[:3]:
        print(f"  - {g['name']} ({g['type']}) {g['time']}")

    print("[2/3] 生成HTML并推送...")
    html = generate_html(games, date_str, update_time)
    if not push_to_github(html, "index.html", f"Update: {date_str} {update_time} ({len(games)} games)"):
        exit(1)

    if send_feishu:
        print("[3/3] 发送飞书通知...")
        token = get_feishu_token()
        send_feishu_card(token, date_str, len(games))
    else:
        print("[3/3] 跳过飞书推送")

    print("=== 完成 ===")
