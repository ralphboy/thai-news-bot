import streamlit as st
import feedparser
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import json
import os
import concurrent.futures
import html
import fcntl

# ================= 1. 頁面設定 (必須放第一行) =================
st.set_page_config(
    page_title="ThaiNews.Ai | 戰情室", 
    page_icon="🇹🇭", 
    layout="wide"
)

# ================= 2. 常數與 CSS 設定 =================

# CSS 美化樣式
CUSTOM_CSS = """
<style>
    .big-font { font-size: 28px !important; font-weight: 800; color: #1a1a1a; margin-bottom: 20px !important; }
    
    /* 緊湊化調整 */
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.5rem !important;
    }
    
    .news-card {
        background-color: white;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        margin-bottom: 8px;
        border-left: 4px solid #d93025;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .news-title {
        font-size: 16px;
        font-weight: 700;
        color: #1a1a1a;
        text-decoration: none;
        display: block;
        margin-bottom: 4px;
    }
    .news-meta { font-size: 13px; color: #666; }
    .news-tag {
        background-color: #f0f0f0;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 11px;
        margin-left: 8px;
        color: #555;
    }
    
    /* 隱藏預設連結符號 */
    .stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a, .stMarkdown h4 a, .stMarkdown h5 a {
        display: none !important;
    }
    
    /* 手機版適配 */
    @media (max-width: 768px) {
        .mobile-hidden { display: none !important; }
        .block-container { padding-top: 2rem !important; }
    }
</style>
"""

# VIP 公司清單
VIP_COMPANIES_EN = [
    '"Delta Electronics"', '"Zhen Ding"', '"Unimicron"', '"Compeq"', 
    '"Gold Circuit Electronics"', '"Dynamic Holding"', '"Tripod Technology"', 
    '"Unitech"', '"Foxconn"', '"Inventec"', '"Garmin"'
]

VIP_COMPANIES_CN = [
    '"台達電"', '"臻鼎"', '"欣興"', '"華通"', 
    '"金像電"', '"定穎"', '"健鼎"', 
    '"燿華"', '"鴻海"', '"英業達"', '"Garmin"'
]

# 預先計算好查詢字串 (避免在函式內重複計算)
VIP_QUERY_EN = "+OR+".join([c.replace(" ", "+") for c in VIP_COMPANIES_EN])
VIP_QUERY_CN = "+OR+".join([c.replace(" ", "+") for c in VIP_COMPANIES_CN])

# 選項映射
DATE_MAP = {
    "1天": 1, "3天": 3, "1週": 7, "1月": 30
}

TOPIC_MAP = {
    "泰國政經": "macro",
    "電子產業": "industry",
    "重點台商": "vip"
}

# 套用 CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ================= 3. 爬蟲核心邏輯 =================

# 各模式的相關性關鍵字（標題必須包含至少一個才保留）
RELEVANCE_KEYWORDS = {
    "macro": [
        "泰國", "泰", "thailand", "thai", "bangkok", "曼谷",
        "台泰", "台商", "東南亞", "asean", "southeast asia",
    ],
    "industry": [
        "泰國", "泰", "thailand", "thai", "bangkok", "曼谷",
        "pcb", "印刷電路板", "電路板", "circuit board",
        "電子製造", "electronics manufacturing",
    ],
    "vip": [
        "泰國", "泰", "thailand", "thai", "bangkok", "曼谷",
        "台達電", "delta electronics", "臻鼎", "zhen ding",
        "欣興", "unimicron", "華通", "compeq",
        "金像電", "gold circuit", "定穎", "dynamic holding",
        "健鼎", "tripod", "燿華", "unitech",
        "鴻海", "foxconn", "英業達", "inventec", "garmin",
        "pcb", "印刷電路板", "台商",
    ],
}


def is_relevant(title, mode):
    """檢查標題是否與搜尋模式相關（至少包含一個關鍵字）"""
    keywords = RELEVANCE_KEYWORDS.get(mode)
    if not keywords:
        return True  # custom 模式不過濾
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in keywords)


def _build_query_templates(mode, custom_keyword=None):
    """
    依搜尋模式產生查詢模板列表。
    每個模板包含 name、query、hl/gl/ceid 參數，日期過濾由呼叫端填入。
    """
    templates = []

    if mode == "custom" and custom_keyword:
        clean_keyword = custom_keyword.strip().replace(" ", "+")
        templates.extend([
            {"name": f"🔍 深度追蹤: {custom_keyword} (中)", "query": clean_keyword,
             "hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"},
            {"name": f"🔍 深度追蹤: {custom_keyword} (EN)", "query": clean_keyword,
             "hl": "en-TH", "gl": "TH", "ceid": "TH:en"},
        ])
    elif mode == "macro":
        templates.extend([
            {"name": "🇹🇭 泰國整體 (中)", "query": "泰國",
             "hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"},
            {"name": "🇹🇭 泰國整體 (EN)", "query": "Thailand",
             "hl": "en-TH", "gl": "TH", "ceid": "TH:en"},
            {"name": "🇹🇼 台泰關係 (中)", "query": "泰國+台灣+OR+%22台商%22",
             "hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"},
            {"name": "🇹🇼 台泰關係 (EN)", "query": "Thailand+Taiwan+OR+%22Taiwanese+investment%22",
             "hl": "en-TH", "gl": "TH", "ceid": "TH:en"},
        ])
    elif mode == "industry":
        templates.extend([
            {"name": "🔌 PCB製造 (中)", "query": "泰國+%22PCB%22+OR+%22印刷電路板%22+OR+%22電子製造%22",
             "hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"},
            {"name": "🔌 PCB製造 (EN)", "query": "Thailand+%22printed+circuit+board%22+OR+%22PCB+manufacturing%22+OR+%22electronics+manufacturing%22",
             "hl": "en-TH", "gl": "TH", "ceid": "TH:en"},
        ])
    elif mode == "vip":
        templates.extend([
            {"name": "🏢 台商動態 (中)", "query": f"泰國+OR+{VIP_QUERY_CN}",
             "hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"},
            {"name": "🏢 台商動態 (EN)", "query": f"Thailand+PCB+OR+{VIP_QUERY_EN}",
             "hl": "en-TH", "gl": "TH", "ceid": "TH:en"},
        ])

    return templates


def get_rss_sources(days, mode="all", custom_keyword=None):
    """
    產生 RSS 來源列表，逐日拆分請求以確保每天都能獨立抓取。
    :param days: 天數 (int)
    """
    templates = _build_query_templates(mode, custom_keyword)
    exclude_sites = "-site:msn.com+-site:aol.com"
    sources = []

    # 逐日產生 RSS URL，每天一個獨立請求
    today = datetime.now().date()
    for day_offset in range(days):
        day_start = today - timedelta(days=day_offset)
        day_end = day_start + timedelta(days=1)
        date_filter = (
            f"after:{day_start.strftime('%Y-%m-%d')}"
            f"+before:{day_end.strftime('%Y-%m-%d')}"
            f"+{exclude_sites}"
        )
        date_label = day_start.strftime('%m/%d')

        for tmpl in templates:
            sources.append({
                "name": f"{tmpl['name']} {date_label}",
                "url": (
                    f"https://news.google.com/rss/search?"
                    f"q={tmpl['query']}+{date_filter}"
                    f"&hl={tmpl['hl']}&gl={tmpl['gl']}&ceid={tmpl['ceid']}"
                ),
                "category": tmpl["name"],  # 用於顯示時歸類（不含日期）
            })

    return sources

def fetch_feed(source):
    """Helper function to fetch a single RSS feed."""
    try:
        return source, feedparser.parse(source['url'])
    except Exception as e:
        return source, None

def is_within_date_range(published_str, days):
    """檢查新聞發布日期是否在指定天數範圍內"""
    if not published_str:
        return True  # 無日期資訊則保留
    try:
        pub_date = parsedate_to_datetime(published_str)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return pub_date >= cutoff
    except Exception:
        return True  # 解析失敗則保留

def generate_chatgpt_prompt(days_label, days_int, search_mode, custom_keyword=None):
    status_text = st.empty() 
    progress_bar = st.progress(0)
    
    # 呼叫 get_rss_sources，並傳入 days_int 作為 days 參數
    sources = get_rss_sources(days_int, search_mode, custom_keyword)
    news_items_for_json = []

    if search_mode == "custom":
        instruction_prompt = f"針對關鍵字【{custom_keyword}】，請撰寫一份深度分析報告：1. 重點摘要 2. 市場影響 3. 機會與風險。"
    elif search_mode == "macro":
        instruction_prompt = f"請分析【{days_label} 泰國整體與台泰關係】：1. 泰國政經局勢 2. 台泰雙邊互動。"
    elif search_mode == "industry":
        instruction_prompt = f"請分析【{days_label} 泰國 PCB 與電子製造】：1. 產業趨勢 2. 供應鏈動態。"
    elif search_mode == "vip":
        instruction_prompt = f"請分析【{days_label} 泰國重點台商】：1. 個股動態 2. 投資訊號。"

    output_text = f"""
請扮演一位資深的「產業分析師」。
{instruction_prompt}
請用**繁體中文**，並以 **Markdown** 條列式輸出，風格需專業且易讀。

========= 以下是新聞資料庫 ({datetime.now().strftime('%Y-%m-%d')}) =========
"""
    
    seen_titles = set()
    total_steps = len(sources)

    # 平行抓取 RSS（逐日拆分後請求數較多，提高併發數）
    max_workers = min(20, len(sources))
    status_text.text(f"📡 正在平行掃描 {len(sources)} 個來源（逐日拆分）...")

    # 按類別收集結果（去除日期後歸類）
    from collections import OrderedDict
    category_entries = OrderedDict()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_source = {executor.submit(fetch_feed, source): source for source in sources}
        concurrent.futures.wait(future_to_source.keys())

        for completed_count, (future, source) in enumerate(future_to_source.items(), 1):
            progress_bar.progress(completed_count / total_steps)

            source, feed = future.result()
            category = source.get('category', source['name'])

            if category not in category_entries:
                category_entries[category] = []

            if feed and len(feed.entries) > 0:
                for entry in feed.entries:
                    if entry.title in seen_titles:
                        continue
                    pub_date = entry.published if 'published' in entry else ""
                    if not is_within_date_range(pub_date, days_int):
                        continue
                    # 相關性過濾：標題須包含至少一個模式關鍵字
                    if not is_relevant(entry.title, search_mode):
                        continue
                    seen_titles.add(entry.title)
                    source_name = entry.source.title if 'source' in entry else "Google News"
                    category_entries[category].append({
                        "title": entry.title, "link": entry.link,
                        "date": pub_date, "source": source_name, "category": category
                    })

    # 按日期排序（新→舊），並分離 prompt 輸出與完整資料
    def _sort_key(item):
        try:
            return parsedate_to_datetime(item["date"]).timestamp()
        except Exception:
            return 0

    for category, entries in category_entries.items():
        # 依日期排序（新→舊）
        entries.sort(key=_sort_key, reverse=True)
        # 全部納入顯示與儲存
        news_items_for_json.extend(entries)

        output_text += f"\n## 【{category}】\n"
        if entries:
            # AI prompt 限制筆數以控制長度，但不影響新聞列表顯示
            prompt_limit = len(entries) if search_mode == "custom" else 50
            for item in entries[:prompt_limit]:
                output_text += f"- [{item['date']}] [{item['source']}] {item['title']}\n  連結: {item['link']}\n"
            if len(entries) > prompt_limit:
                output_text += f"  ...（另有 {len(entries) - prompt_limit} 篇，見下方新聞列表）\n"
        else:
            output_text += "(無相關新聞)\n"

    output_text += "\n========= 資料結束 ========="
    
    # 累積歷史資料邏輯（加檔案鎖防止並發寫入損毀）
    MAX_NEWS_ITEMS = 5000  # 歷史上限，避免無限增長
    try:
        with open('news_data.json', 'a+', encoding='utf-8') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.seek(0)
                content = f.read()
                existing_data = json.loads(content) if content.strip() else {"news_list": []}
            except json.JSONDecodeError:
                existing_data = {"news_list": []}

            # 建立現有連結集合以過濾重複
            existing_links = set(item['link'] for item in existing_data.get('news_list', []))

            for item in news_items_for_json:
                if item['link'] not in existing_links:
                    existing_data['news_list'].insert(0, item)
                    existing_links.add(item['link'])

            # 超過上限則裁切舊資料
            existing_data['news_list'] = existing_data['news_list'][:MAX_NEWS_ITEMS]
            existing_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            f.seek(0)
            f.truncate()
            json.dump(existing_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"存檔失敗: {e}")

    status_text.text("✅ 完成！")
    time.sleep(0.5)
    status_text.empty()
    progress_bar.empty()
    
    return output_text, news_items_for_json

def display_results(prompt, news_list):
    """顯示搜尋結果的共用函數"""
    st.markdown("##### 1. AI 分析指令")
    with st.expander("點擊展開查看 Prompt", expanded=True):
        st.code(prompt, language="markdown")
        
    st.markdown("##### 2. 相關新聞速覽")
    if news_list:
        for news in news_list:
            cat = news.get('category', '一般')
            # Security fix: Escape HTML special characters
            safe_title = html.escape(news['title'])
            safe_source = html.escape(news['source'])
            safe_link = html.escape(news.get('link', '#'))

            st.markdown(f'''
            <div class="news-card">
                <a href="{safe_link}" target="_blank" class="news-title">{safe_title}</a>
                <div class="news-meta">{news['date']} • {safe_source} <span class="news-tag">{cat}</span></div>
            </div>
            ''', unsafe_allow_html=True)
    else:
        st.warning("查無新聞資料。")

# ================= 4. 網頁主程式 =================

st.markdown('<div class="big-font">ThaiNews.Ai 🇹🇭 戰情室</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🤖 生成器", "📊 歷史庫"])

with tab1:
    # 核心版面：左控右顯
    c_left, c_right = st.columns([1, 3], gap="medium")
    
    with c_left:
        st.markdown('<h5 class="mobile-hidden">⚙️ 設定操作</h5>', unsafe_allow_html=True)
        
        # [狀態管理]
        if 'days_int' not in st.session_state: st.session_state['days_int'] = 1 
        if 'search_type' not in st.session_state: st.session_state['search_type'] = None
        if 'search_keyword' not in st.session_state: st.session_state['search_keyword'] = ""
        if 'last_topic' not in st.session_state: st.session_state['last_topic'] = None
        
        # [Helper] 設定搜尋模式
        def set_search(mode, keyword=""):
            st.session_state['search_type'] = mode
            st.session_state['search_keyword'] = keyword

        # 1. 時間選擇
        st.caption("1. 時間範圍")
        # 注意: st.pills 需要 Streamlit 1.40.0+
        try:
            date_selection = st.pills("Time", list(DATE_MAP.keys()), default="1天", label_visibility="collapsed", key="pills_date")
        except AttributeError:
            st.error("請更新 Streamlit 版本至 1.40+ 以使用 Pills 元件，或改用 Radio。")
            date_selection = st.radio("Time", list(DATE_MAP.keys()), horizontal=True, label_visibility="collapsed")
            
        if date_selection:
            st.session_state['days_int'] = DATE_MAP[date_selection] 

        # 2. 主題選擇
        st.caption("2. 分析主題")
        try:
            topic_selection = st.pills("Topic", list(TOPIC_MAP.keys()), label_visibility="collapsed", selection_mode="single", key="pills_topic")
        except AttributeError:
            topic_selection = st.radio("Topic", ["(請選擇)"] + list(TOPIC_MAP.keys()), label_visibility="collapsed")
            if topic_selection == "(請選擇)": topic_selection = None
        
        if topic_selection:
            target_mode = TOPIC_MAP[topic_selection]
            if st.session_state.get('last_topic') != topic_selection:
                st.session_state['last_topic'] = topic_selection 
                set_search(target_mode)
                st.rerun() 
        
        # 3. 自訂搜尋
        st.caption("3. 關鍵字")
        def handle_custom_search():
            kw = st.session_state.kw_input
            if kw:
                # 清除主題選取 (如果使用 pills)
                try:
                    st.session_state['pills_topic'] = None 
                except:
                    pass
                st.session_state['last_topic'] = None
                set_search("custom", kw)

        c_in, c_btn = st.columns([3, 1], gap="small")
        with c_in:
            st.text_input("Keywords", placeholder="輸入關鍵字", key="kw_input", on_change=handle_custom_search, label_visibility="collapsed")
        with c_btn:
            st.button("🔍", type="primary", use_container_width=True, on_click=handle_custom_search)

    # 右側：顯示結果區域
    with c_right:
        days_int = st.session_state['days_int']
        selected_label = next((k for k, v in DATE_MAP.items() if v == days_int), f"{days_int}天")
        
        s_type = st.session_state.get('search_type')
        s_kw = st.session_state.get('search_keyword')

        # 搜尋模式對應的 spinner 文字
        SPINNER_MAP = {
            "macro": "正在掃描泰國大選、經貿與台泰新聞...",
            "industry": "正在掃描 PCB 與電子供應鏈新聞...",
            "vip": "正在掃描重點台商動態...",
        }

        # 尚未搜尋時的歡迎畫面
        if not s_type:
            st.info("👈 請從左側選擇主題或輸入關鍵字開始。")
            st.markdown("""
            <div style="background:#f8f9fa; padding:15px; border-radius:10px; color:#555;">
                <strong>💡 系統說明：</strong><br>
                1. <b>泰國政經</b>：政經局勢與台泰關係。<br>
                2. <b>電子產業</b>：PCB、伺服器與電子製造。<br>
                3. <b>重點台商</b>：鎖定 11 大指標台廠動態。
            </div>
            """, unsafe_allow_html=True)

        # 執行搜尋
        elif s_type == "custom" and s_kw:
            with st.spinner(f"正在全網搜索 {s_kw}..."):
                prompt, news_list = generate_chatgpt_prompt(selected_label, days_int, "custom", s_kw)
                display_results(prompt, news_list)
        elif s_type in SPINNER_MAP:
            with st.spinner(SPINNER_MAP[s_type]):
                prompt, news_list = generate_chatgpt_prompt(selected_label, days_int, s_type)
                display_results(prompt, news_list)

with tab2:
    col_head_1, col_head_2 = st.columns([3, 1])
    with col_head_1:
        st.markdown("### 📂 歷史新聞資料庫")
    with col_head_2:
        if st.button("🔄 刷新列表"): st.rerun()
    
    if os.path.exists('news_data.json'):
        with open('news_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        news_list = data.get('news_list', [])
        st.caption(f"📅 上次更新: {data.get('timestamp', '未知')} (共 {len(news_list)} 則)")

        search_query = st.text_input("🔍 搜尋歷史...", placeholder="請輸入標題關鍵字")
        if search_query:
            news_list = [n for n in news_list if search_query.lower() in n['title'].lower()]

        if news_list:
            for news in news_list:
                cat = html.escape(news.get('category', '歷史'))
                safe_title = html.escape(news['title'])
                safe_source = html.escape(news['source'])
                safe_link = html.escape(news.get('link', '#'))
                st.markdown(f"""
                <div class="news-card">
                    <a href="{safe_link}" target="_blank" class="news-title">{safe_title}</a>
                    <div class="news-meta">{news['date']} • {safe_source} <span class="news-tag">{cat}</span></div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("無符合資料")
    else:
        st.info("尚無歷史紀錄，請先在生成器執行搜尋。")