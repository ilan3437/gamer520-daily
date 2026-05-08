"""
Gamer520 每日PC游戏更新 - GitHub Actions 版
使用 Puppeteer 绕过 Cloudflare 抓取游戏数据
"""
import requests
import json
import re
import base64
import os
import subprocess
from datetime import datetime

# ========== 配置 ==========
SITE_URL = "https://www.gamer520.com/pcplay"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "ilan3437/gamer520-daily")
GITHUB_API = "https://api.github.com"
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_API = "https://open.feishu.cn/open-apis"
CLOUDFLARE_URL = "https://gamer520-daily.pages.dev"

# ========== 类型推断 ==========
TYPE_RULES = [
    (['战记', '战争', '三国', '战国'], '策略/战棋'),
    (['模拟器', '天际线', '加油站', '经销商', '驿站', '挖矿', '创业', '农庄', '卡车'], '模拟/经营'),
    (['RPG', '英雄无敌', '武侠', '明末', '英雄传', '大宋'], '角色扮演'),
    (['生存', '深空', '感染', '劫后'], '生存/冒险'),
    (['格斗', '无双', '战斗之潮', '电锯姬', '圣杯'], '动作/格斗'),
    (['卡牌', '恶魔牌', '弈战'], '卡牌/策略'),
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

def get_proxy_url(url):
    if url and url.startswith('http'):
        return f"https://wsrv.nl/?url={url.replace('https://', '')}&w=160&h=90&fit=cover"
    return url

def extract_time_from_article(article):
    m = re.search(r'(\d+\s*小时前|\d+\s*天前|昨天)', article)
    if m:
        return m.group(1).replace(' ', '')
    return ''

def time_to_hours(t):
    m = re.search(r'(\d+)小时前', t)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)天前', t)
    if m:
        return int(m.group(1)) * 24 + 100
    return 999

def fetch_pages_with_puppeteer():
    """使用 Puppeteer 抓取页面内容，绕过 Cloudflare"""
    puppeteer_script = r'''
const puppeteer = require('puppeteer');
(async () => {
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    });
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36');
    const urls = process.argv.slice(2);
    const results = [];
    for (const url of urls) {
        try {
            await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
            await new Promise(r => setTimeout(r, 3000));
            const html = await page.content();
            results.push(html);
        } catch(e) {
            results.push('');
        }
    }
    console.log('===PAGE_START===');
    for (const html of results) {
        console.log('===PAGE===');
        console.log(html);
    }
    console.log('===PAGE_END===');
    await browser.close();
})();
'''
    urls = [SITE_URL] + [f"{SITE_URL}/page/{p}" for p in range(2, 6)]

    script_path = '/tmp/fetch_gamer520.js'
    with open(script_path, 'w') as f:
        f.write(puppeteer_script)

    print("使用 Puppeteer 抓取...")
    result = subprocess.run(
        ['node', script_path] + urls,
        capture_output=True, text=True, timeout=180
    )

    if result.returncode != 0:
        print(f"Puppeteer 错误: {result.stderr[:500]}")
        return []

    output = result.stdout
    pages = []
    if '===PAGE_START===' in output and '===PAGE_END===' in output:
        content = output.split('===PAGE_START===')[1].split('===PAGE_END===')[0]
        pages = content.split('===PAGE===')[1:]

    print(f"获取到 {len(pages)} 页内容")
    return pages

def parse_games_from_html(pages):
    """从 HTML 页面解析游戏数据"""
    games = []
    for page_idx, html in enumerate(pages):
        page_num = page_idx + 1
        print(f"处理第{page_num}页 (长度: {len(html)})...")

        if len(html) < 1000:
            print(f"  内容太短，跳过")
            continue

        all_hours = [int(t) for t in re.findall(r'(\d+)\s*小时前', html)]
        page_time = f'{min(all_hours)}小时前' if all_hours else ''
        print(f"  页面时间: {page_time}")

        articles = re.findall(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
        print(f"  找到 {len(articles)} 篇文章")

        for article in articles:
            link_match = re.search(r'<a[^>]+href="(https://www\.gamer520\.com/\d+\.html)"', article)
            if not link_match:
                continue
            link = link_match.group(1)

            img_match = re.search(r'data-src="([^"]+)"', article)
            if not img_match:
                img_match = re.search(r'src="([^"]+)"', article)
            img_url = img_match.group(1) if img_match else ''

            if not any(d in img_url for d in ['imagehub', 'steamstatic', 'queniuqe', 'akamai']):
                continue

            name_match = re.search(r'alt="([^"]+)"', article)
            if name_match:
                name = name_match.group(1).split('|')[0].strip()
            else:
                name = ''

            if not name or name in [g['name'] for g in games]:
                continue

            article_time = extract_time_from_article(article)
            if not article_time:
                article_time = page_time

            games.append({
                'name': name,
                'type': get_game_type(name),
                'time': article_time,
                'cover': get_proxy_url(img_url),
                'link': link
            })

        if page_time:
            m = re.search(r'(\d+)小时前', page_time)
            if m and int(m.group(1)) > 24:
                print(f"  超过24小时，停止翻页")
                break

    games.sort(key=lambda g: time_to_hours(g['time']))
    return games

def fetch_games():
    """主抓取函数：从 Puppeteer 输出的 JSON 文件读取页面"""
    pages = []
    pages_file = '/tmp/pages.json'
    
    if os.path.exists(pages_file):
        try:
            with open(pages_file, 'r', encoding='utf-8') as f:
                pages = json.load(f)
            print(f"从 {pages_file} 读取到 {len(pages)} 页内容")
        except Exception as e:
            print(f"读取 pages.json 失败: {e}")
    
    if not pages:
        print("Puppeteer 未获取到页面，尝试 requests...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            resp = requests.get(SITE_URL, timeout=20, headers=headers)
            if len(resp.text) > 1000:
                pages = [resp.text]
        except Exception as e:
            print(f"requests 也失败: {e}")

    return parse_games_from_html(pages)

def generate_html(games, date_str, update_time):
    games_json = json.dumps(games, ensure_ascii=False)
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gamer520 PC游戏更新 - {date_str}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;900&display=swap');
:root {{--bg:#0a0a0f;--card:#14141f;--border:#2a2a3e;--accent:#00e68a;--text:#e8e8f0;--text-dim:#8888a0;}}
* {{margin:0;padding:0;box-sizing:border-box;}}
body {{font-family:'Noto Sans SC',sans-serif;background:var(--bg);color:var(--text);padding:20px 16px;max-width:600px;margin:0 auto;min-height:100vh;}}
.header {{text-align:center;margin-bottom:20px;padding-bottom:16px;border-bottom:1px solid var(--border);}}
.header h1 {{font-size:22px;font-weight:900;background:linear-gradient(135deg,#00e68a,#00b8ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}}
.header .date {{font-size:13px;color:var(--text-dim);margin-top:4px;}}
.header .count {{font-size:12px;color:var(--accent);background:rgba(0,230,138,0.1);padding:4px 12px;border-radius:20px;display:inline-block;margin-top:8px;}}
.refresh-btn {{display:inline-flex;align-items:center;gap:6px;background:linear-gradient(135deg,var(--accent),#00b8ff);color:#000;border:none;padding:8px 16px;border-radius:20px;font-size:13px;font-weight:600;cursor:pointer;margin-top:12px;}}
.refresh-btn:hover {{transform:scale(1.05);}}
.game-card {{display:flex;align-items:center;gap:12px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:10px;margin-bottom:8px;text-decoration:none;color:inherit;transition:all 0.2s;animation:fadeIn 0.4s ease backwards;}}
@keyframes fadeIn {{from{{opacity:0;transform:translateY(10px);}}to{{opacity:1;transform:translateY(0);}}}}
.game-cover-wrapper {{width:80px;height:45px;border-radius:6px;flex-shrink:0;background:linear-gradient(135deg,#1e1e30,#2a2a3e);overflow:hidden;position:relative;}}
.game-cover {{width:100%;height:100%;object-fit:cover;cursor:zoom-in;}}
.game-cover-placeholder {{position:absolute;top:0;left:0;width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:20px;}}
.game-info {{flex:1;min-width:0;}}
.game-name {{font-size:14px;font-weight:700;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:4px;}}
.game-meta {{display:flex;align-items:center;gap:6px;}}
.game-tag {{font-size:11px;color:var(--accent);background:rgba(0,230,138,0.1);border:1px solid rgba(0,230,138,0.25);padding:1px 6px;border-radius:4px;}}
.game-time {{font-size:11px;color:var(--text-dim);}}
.footer {{text-align:center;padding:16px;font-size:11px;color:var(--text-dim);margin-top:8px;}}
.footer a {{color:var(--accent);text-decoration:none;}}
.lightbox {{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.95);z-index:1000;justify-content:center;align-items:center;padding:20px;}}
.lightbox.active {{display:flex;}}
.lightbox img {{max-width:100%;max-height:80vh;border-radius:8px;}}
.lightbox-close {{position:absolute;top:20px;right:20px;width:40px;height:40px;background:rgba(255,255,255,0.1);border:none;border-radius:50%;color:#fff;font-size:24px;cursor:pointer;}}
.toast {{position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:var(--card);border:1px solid var(--border);padding:12px 20px;border-radius:8px;font-size:13px;z-index:1001;opacity:0;transition:opacity 0.3s;}}
.toast.show {{opacity:1;}}
</style>
</head>
<body>
<div class="header">
    <h1>🎮 Gamer520 PC游戏更新</h1>
    <div class="date">{date_str}</div>
    <span class="count" id="count">共 {len(games)} 款</span>
    <br>
    <button class="refresh-btn" onclick="handleRefresh()">🔄 刷新数据</button>
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
        listEl.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-dim)">暂无数据</div>';
        return;
    }}
    countEl.textContent = `共 ${{games.length}} 款`;
    listEl.innerHTML = games.map((game, i) => `
        <a class="game-card" href="${{game.link}}" target="_blank" style="animation-delay:${{i*0.03}}s">
            <div class="game-cover-wrapper">
                <img class="game-cover" src="${{game.cover}}" alt="" loading="lazy"
                     onerror="this.style.display='none';this.nextElementSibling.style.display='flex';"
                     onload="this.style.display='block';this.nextElementSibling.style.display='none';"
                     onclick="event.preventDefault();openLightbox('${{game.cover}}')">
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
function openLightbox(src) {{if(!src)return;document.getElementById('lightboxImg').src=src;document.getElementById('lightbox').classList.add('active');document.body.style.overflow='hidden';}}
function closeLightbox() {{document.getElementById('lightbox').classList.remove('active');document.body.style.overflow='';}}
function showToast(msg) {{const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),3000);}}
async function handleRefresh() {{
    try {{
        const resp = await fetch(GITHUB_RAW+'?t='+Date.now());
        if(!resp.ok)throw new Error();
        const html = await resp.text();
        const m = html.match(/let GAMES_DATA = (\[[\s\S]*?\]);/);
        if(m) {{GAMES_DATA=JSON.parse(m[1]);renderGames(GAMES_DATA);showToast('已刷新');}}
    }} catch(e) {{showToast('刷新失败');}}
}}
document.addEventListener('keydown',e=>{{if(e.key==='Escape')closeLightbox();}});
renderGames(GAMES_DATA);
</script>
</body>
</html>'''

def push_to_github(content, filename="index.html"):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    get_resp = requests.get(url, headers=headers)
    sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None
    data = {
        "message": f"Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        "branch": "main"
    }
    if sha:
        data["sha"] = sha
    resp = requests.put(url, headers=headers, json=data)
    return resp.status_code in [200, 201]

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
    for chat in chats:
        chat_id = chat.get("chat_id")
        chat_name = chat.get("name", "未知")
        card = {
            "config": {"wide_screen_mode": True},
            "header": {"title": {"tag": "plain_text", "content": f"\U0001f3ae Gamer520 今日更新 ({date_str})"}, "template": "green"},
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": f"**{game_count}** 款新游戏已更新"}},
                {"tag": "action", "actions": [{"tag": "button", "text": {"tag": "plain_text", "content": "\U0001f4f1 查看游戏列表"}, "type": "primary", "url": CLOUDFLARE_URL}]},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": "每小时自动更新 | 点击封面可放大"}]}
            ]
        }
        resp = requests.post(f"{FEISHU_API}/im/v1/messages", params={"receive_id_type": "chat_id"}, headers={"Authorization": f"Bearer {token}"}, json={"receive_id": chat_id, "msg_type": "interactive", "content": json.dumps(card)})
        if resp.json().get("code") == 0:
            print(f"\u2705 飞书已发送到「{chat_name}」")

if __name__ == "__main__":
    import sys
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    update_time = now.strftime('%H:%M')

    force_feishu = '--feishu' in sys.argv
    send_feishu = force_feishu or os.environ.get("SEND_FEISHU", "false").lower() == "true"

    print(f"=== Gamer520 更新 ({date_str} {update_time}) ===")
    games = fetch_games()
    print(f"抓取到 {len(games)} 款游戏")

    if not games:
        print("没有新游戏，跳过")
        exit(0)

    for g in games[:5]:
        print(f"  - {g['name']} ({g['time']})")

    html = generate_html(games, date_str, update_time)
    if not push_to_github(html, "index.html"):
        exit(1)

    if send_feishu:
        token = get_feishu_token()
        send_feishu_card(token, date_str, len(games))

    print("=== 完成 ===")
