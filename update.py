"""
Gamer520 姣忔棩PC娓告垙鏇存柊 - GitHub Actions 鐗?浠庣綉绔欐姄鍙栧綋澶╂父鎴?鈫?鐢熸垚HTML 鈫?鎺ㄩ€佸埌GitHub 鈫?Cloudflare/Vercel鑷姩閮ㄧ讲
"""
import requests
import json
import re
import base64
import os
from datetime import datetime
from bs4 import BeautifulSoup

# ========== 閰嶇疆 ==========
SITE_URL = "https://www.gamer520.com/pcplay"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "ilan3437/gamer520-daily")
GITHUB_API = "https://api.github.com"

# 椋炰功閰嶇疆锛堜粠鐜鍙橀噺璇诲彇锛?FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_API = "https://open.feishu.cn/open-apis"

# 缃戦〉鍦板潃
CLOUDFLARE_URL = "https://gamer520-daily.pages.dev"

# ========== 绫诲瀷鎺ㄦ柇 ==========
TYPE_RULES = [
    (['鎴樿', '鎴樹簤', '涓夊浗', '鎴樺浗'], '绛栫暐/鎴樻'),
    (['妯℃嫙鍣?, '澶╅檯绾?, '鍔犳补绔?, '缁忛攢鍟?, '椹跨珯', '鎸栫熆', '鍒涗笟', '鍐滃簞', '鍗¤溅'], '妯℃嫙/缁忚惀'),
    (['RPG', '鑻遍泟鏃犳晫', '姝︿緺', '鏄庢湯', '鑻遍泟浼?, '澶у畫'], '瑙掕壊鎵紨'),
    (['鐢熷瓨', '娣辩┖', '鎰熸煋', '鍔悗'], '鐢熷瓨/鍐掗櫓'),
    (['鏍兼枟', '鏃犲弻', '鎴樻枟涔嬫疆', '鐢甸敮濮?, '鍦ｆ澂'], '鍔ㄤ綔/鏍兼枟'),
    (['鍗＄墝', '鐗?, '鎭堕瓟鐗?, '寮堟垬'], '鍗＄墝/绛栫暐'),
    (['鑷蛋妫?, '鍥㈡湰'], '绛栫暐/鑷蛋妫?),
    (['鎭嬬埍', '鐗╄', '澶╀娇'], '瑙嗚灏忚'),
    (['濉旈槻', '鐐'], '绛栫暐/濉旈槻'),
    (['鎽搁奔', '鏀剧疆'], '鏀剧疆/妯℃嫙'),
    (['浜戞棌瑁?, 'inZOI'], '妯℃嫙/鐢熸椿'),
    (['鏈€缁堝够鎯?, 'FF'], 'JRPG/鍔ㄤ綔'),
    (['寮€鎷撹€?, '姝ｄ箟涔嬫€?], 'RPG/绛栫暐'),
    (['鎺ㄥ竵鏈?, '鐏煷浜?], '浼戦棽/妯℃嫙'),
    (['杩柉绉?], '鑺傚/鏍兼枟'),
    (['璺戦叿'], '璺戦叿/鍔ㄤ綔'),
]

def get_game_type(name):
    for keywords, gtype in TYPE_RULES:
        for kw in keywords:
            if kw in name:
                return gtype
    return '鍔ㄤ綔/鍐掗櫓'

def get_proxy_image_url(url):
    """浣跨敤鍥剧墖浠ｇ悊瑙ｅ喅鍥藉唴璁块棶闂"""
    if not url:
        return ''
    # 浣跨敤 wsrv.nl 浠ｇ悊鏈嶅姟
    if url.startswith('http'):
        # 缂栫爜URL
        encoded = url.replace('https://', '').replace('http://', '')
        return f"https://wsrv.nl/?url={encoded}&w=160&h=90&fit=cover"
    return url

# ========== 鎶撳彇娓告垙 ==========
def fetch_games():
    """鎶撳彇褰撳ぉ鏇存柊鐨勬父鎴忥紙鍙姄鍙栭〉闈㈠簳閮ㄧ殑缁熶竴鏃堕棿鍦?4灏忔椂鍐呯殑锛?""
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

            # 鑾峰彇椤甸潰搴曢儴鐨勭粺涓€鏇存柊鏃堕棿
            page_time = ''
            nav = soup.find('nav', class_='pagination') or soup.find('div', class_='nav-links')
            if nav:
                prev_text = nav.find_previous_sibling(string=True)
                if prev_text:
                    time_match = re.search(r'(\d+灏忔椂鍓峾\d+澶╁墠|鏄ㄥぉ)', prev_text)
                    if time_match:
                        page_time = time_match.group(1)

            # 濡傛灉娌℃壘鍒帮紝浠庨〉闈㈡枃鏈腑鎵?            if not page_time:
                page_text = soup.get_text()
                time_matches = re.findall(r'(\d+灏忔椂鍓峾\d+澶╁墠|鏄ㄥぉ)', page_text)
                if time_matches:
                    page_time = time_matches[-1]

            # 濡傛灉椤甸潰鏃堕棿瓒呰繃24灏忔椂锛屽仠姝㈢炕椤?            if page_time:
                hour_match = re.search(r'(\d+)灏忔椂鍓?, page_time)
                if hour_match:
                    hours = int(hour_match.group(1))
                    if hours > 24:
                        print(f"  绗瑊page}椤垫洿鏂颁簬{page_time}锛岃秴杩?4灏忔椂锛屽仠姝㈢炕椤?)
                        break
                day_match = re.search(r'(\d+)澶╁墠', page_time)
                if day_match:
                    days = int(day_match.group(1))
                    if days >= 1:
                        print(f"  绗瑊page}椤垫洿鏂颁簬{page_time}锛岃秴杩?4灏忔椂锛屽仠姝㈢炕椤?)
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
                    if not title or '瑙ｅ帇鍗虫捀' not in title:
                        continue

                    name = title.split('|')[0].strip()

                    # 鑾峰彇灏侀潰鍥惧苟浣跨敤浠ｇ悊
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
            print(f"  鎶撳彇绗瑊page}椤靛け璐? {e}")
            continue

    # 鍘婚噸
    seen = set()
    unique = []
    for g in games:
        if g['name'] not in seen:
            seen.add(g['name'])
            unique.append(g)

    # 鎸夋椂闂存帓搴忥細鏈€鏂扮殑鏀惧墠闈?    def sort_key(g):
        t = g['time']
        # 鎻愬彇灏忔椂鏁帮紝鏁板瓧瓒婂皬瓒婃柊
        m = re.search(r'(\d+)', t)
        if m:
            return int(m.group(1))
        return 999
    unique.sort(key=sort_key)

    return unique

# ========== 鐢熸垚HTML ==========
def generate_html(games, date_str, update_time):
    """鐢熸垚娓告垙鍒楄〃HTML"""

    games_json = json.dumps(games, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>Gamer520 PC娓告垙鏇存柊 - {date_str}</title>
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
    <h1>馃幃 Gamer520 PC娓告垙鏇存柊</h1>
    <div class="date">{date_str}</div>
    <span class="count" id="count">鍏?{len(games)} 娆?/span>
    <br>
    <button class="refresh-btn" id="refreshBtn" onclick="handleRefresh()">
        <span class="spinner"></span>
        <span class="btn-text">馃攧 鍒锋柊鏁版嵁</span>
    </button>
</div>
<div class="list" id="gameList"></div>
<div class="footer">
    <span id="updateTime">鏇存柊鏃堕棿: {update_time}</span> | <a href="{SITE_URL}" target="_blank">璁块棶鍘熺綉绔?/a>
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
        listEl.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-dim)">浠婂ぉ鏆傛棤鏂版父鎴?/div>';
        countEl.textContent = '鍏?0 娆?;
        return;
    }}
    countEl.textContent = `鍏?${{games.length}} 娆綻;
    listEl.innerHTML = games.map((game, i) => `
        <a class="game-card" href="${{game.link}}" target="_blank" style="animation-delay:${{i*0.03}}s">
            <div class="game-cover-wrapper">
                <img class="game-cover" src="${{game.cover}}" alt="" loading="lazy"
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';"
                     onload="this.style.display='block'; this.nextElementSibling.style.display='none';"
                     onclick="event.preventDefault(); openLightbox('${{game.cover}}')">
                <div class="game-cover-placeholder">馃幃</div>
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
            showToast('宸插埛鏂帮紝鍏?' + GAMES_DATA.length + ' 娆?);
        }} else {{
            showToast('鏈壘鍒版暟鎹?);
        }}
    }} catch(e) {{
        showToast('鍒锋柊澶辫触');
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

# ========== GitHub鎿嶄綔 ==========
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
        print(f"鉁?鎺ㄩ€佹垚鍔? {filename}")
        return True
    else:
        print(f"鉂?鎺ㄩ€佸け璐? {resp.json()}")
        return False

# ========== 椋炰功鎺ㄩ€?==========
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
        chat_name = chat.get("name", "鏈煡")

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"馃幃 Gamer520 浠婃棩鏇存柊 ({date_str})"},
                "template": "green"
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": f"**{game_count}** 娆炬柊娓告垙宸叉洿鏂?}},
                {"tag": "action", "actions": [
                    {"tag": "button", "text": {"tag": "plain_text", "content": "馃摫 鏌ョ湅娓告垙鍒楄〃"}, "type": "primary", "url": CLOUDFLARE_URL}
                ]},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": "姣忓皬鏃惰嚜鍔ㄦ洿鏂?| 鐐瑰嚮灏侀潰鍙斁澶?}]}
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
            print(f"鉁?椋炰功宸插彂閫佸埌銆寋chat_name}銆?)
        else:
            print(f"鉂?椋炰功鍙戦€佸け璐? {result.get('msg')}")

# ========== 涓诲嚱鏁?==========
if __name__ == "__main__":
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    update_time = now.strftime('%H:%M')
    send_feishu = os.environ.get("SEND_FEISHU", "false").lower() == "true"

    print(f"=== Gamer520 鏇存柊 ({date_str} {update_time}) ===")

    print("[1/3] 鎶撳彇娓告垙...")
    games = fetch_games()
    print(f"  鎶撳彇鍒?{len(games)} 娆炬父鎴?)

    if not games:
        print("  娌℃湁鏂版父鎴忥紝璺宠繃")
        exit(0)

    for g in games[:3]:
        print(f"  - {g['name']} ({g['type']}) {g['time']}")

    print("[2/3] 鐢熸垚HTML骞舵帹閫?..")
    html = generate_html(games, date_str, update_time)
    if not push_to_github(html, "index.html", f"Update: {date_str} {update_time} ({len(games)} games)"):
        exit(1)

    if send_feishu:
        print("[3/3] 鍙戦€侀涔﹂€氱煡...")
        token = get_feishu_token()
        send_feishu_card(token, date_str, len(games))
    else:
        print("[3/3] 璺宠繃椋炰功鎺ㄩ€?)

    print("=== 瀹屾垚 ===")
