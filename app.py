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

def _build_date_filter(date_after_str, date_before_str):
    """建立單日的日期過濾與排除參數"""
    exclude_sites = "-site:msn.com+-site:aol.com"
    return f"after:{date_after_str}+before:{date_before_str}+{exclude_sites}"


def _build_sources_for_filter(date_filter, mode, custom_keyword=None, day_label=""):
    """根據模式與日期過濾條件產生 RSS 來源列表"""
    sources = []
    suffix = f" {day_label}" if day_label else ""

    if mode == "custom" and custom_keyword:
        clean_keyword = custom_keyword.strip().replace(" ", "+")
        sources.append({
            "name": f"🔍 深度追蹤: {custom_keyword} (中){suffix}",
            "url": f"https://news.google.com/rss/search?q={clean_keyword}+{date_filter}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        })
        sources.append({
            "name": f"🔍 深度追蹤: {custom_keyword} (EN){suffix}",
            "url": f"https://news.google.com/rss/search?q={clean_keyword}+{date_filter}&hl=en-TH&gl=TH&ceid=TH:en"
        })
    elif mode == "macro":
        sources.extend([
            {"name": f"🇹🇭 泰國整體 (中){suffix}", "url": f"https://news.google.com/rss/search?q=泰國+{date_filter}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"},
            {"name": f"🇹🇭 泰國整體 (EN){suffix}", "url": f"https://news.google.com/rss/search?q=Thailand+{date_filter}&hl=en-TH&gl=TH&ceid=TH:en"},
            {"name": f"🇹🇼 台泰關係 (中){suffix}", "url": f"https://news.google.com/rss/search?q=泰國+台灣+OR+%22台商%22+{date_filter}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"},
            {"name": f"🇹🇼 台泰關係 (EN){suffix}", "url": f"https://news.google.com/rss/search?q=Thailand+Taiwan+OR+%22Taiwanese+investment%22+{date_filter}&hl=en-TH&gl=TH&ceid=TH:en"}
        ])
    elif mode == "industry":
        sources.extend([
            {"name": f"🔌 PCB製造 (中){suffix}", "url": f"https://news.google.com/rss/search?q=泰國+%22PCB%22+OR+%22印刷電路板%22+OR+%22電子製造%22+{date_filter}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"},
            {"name": f"🔌 PCB製造 (EN){suffix}", "url": f"https://news.google.com/rss/search?q=Thailand+%22printed+circuit+board%22+OR+%22PCB+manufacturing%22+OR+%22electronics+manufacturing%22+{date_filter}&hl=en-TH&gl=TH&ceid=TH:en"}
        ])
    elif mode == "vip":
        sources.extend([
            {"name": f"🏢 台商動態 (中){suffix}", "url": f"https://news.google.com/rss/search?q=泰國+OR+{VIP_QUERY_CN}+{date_filter}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"},
            {"name": f"🏢 台商動態 (EN){suffix}", "url": f"https://news.google.com/rss/search?q=Thailand+PCB+OR+{VIP_QUERY_EN}+{date_filter}&hl=en-TH&gl=TH&ceid=TH:en"}
        ])

    return sources


def get_rss_sources(days, mode="all", custom_keyword=None):
    """
    產生 RSS 來源列表
    :param days: 天數 (int)
    當天數 > 1 時，逐日拆分請求以避免 Google News RSS 只回傳最近結果的問題
    """
    # 短天數 (1天) 不需拆分，直接用單一區間
    if days <= 1:
        date_after = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        date_before = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        date_filter = _build_date_filter(date_after, date_before)
        return _build_sources_for_filter(date_filter, mode, custom_keyword)

    # 天數 > 1：逐日拆分，每天各自發請求
    all_sources = []
    for i in range(days):
        day_start = datetime.now() - timedelta(days=days - i)
        day_end = day_start + timedelta(days=1)
        date_after = day_start.strftime('%Y-%m-%d')
        date_before = day_end.strftime('%Y-%m-%d')
        day_label = day_start.strftime('%m/%d')
        date_filter = _build_date_filter(date_after, date_before)
        all_sources.extend(
            _build_sources_for_filter(date_filter, mode, custom_keyword, day_label)
        )

    return all_sources

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
    
    # 平行抓取 RSS
    status_text.text(f"📡 正在平行掃描 {len(sources)} 個來源...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # 建立 future，並保留原始順序索引
        futures = []
        for idx, source in enumerate(sources):
            future = executor.submit(fetch_feed, source)
            futures.append((idx, future))

        # 等待所有抓取完成
        concurrent.futures.wait([f for _, f in futures])

        # 按原始順序收集結果
        results = [None] * len(sources)
        for idx, future in futures:
            results[idx] = future.result()

        for completed_count, (source, feed) in enumerate(results, 1):
            progress_bar.progress(completed_count / total_steps)

            if feed and len(feed.entries) > 0:
                # 自訂搜尋不設限，預設限制 30 篇
                limit = len(feed.entries) if search_mode == "custom" else 30

                for entry in feed.entries[:limit]:
                    if entry.title in seen_titles: continue
                    pub_date = entry.published if 'published' in entry else ""
                    # 過濾超出時間範圍的新聞
                    if not is_within_date_range(pub_date, days_int):
                        continue
                    seen_titles.add(entry.title)
                    source_name = entry.source.title if 'source' in entry else "Google News"
                    # 去掉日期後綴，用基礎類別名顯示
                    base_category = source['name'].rsplit(' ', 1)[0] if any(c.isdigit() for c in source['name'].split()[-1]) else source['name']
                    output_text += f"- [{pub_date}] [{source_name}] {entry.title}\n  連結: {entry.link}\n"
                    news_items_for_json.append({
                        "title": entry.title, "link": entry.link, "date": pub_date,
                        "source": source_name, "category": base_category
                    })

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