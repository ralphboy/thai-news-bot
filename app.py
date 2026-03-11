import streamlit as st
import feedparser
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import json
import os
import concurrent.futures
from collections import OrderedDict
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

# VIP 公司清單：顯示名 → {泰國中文名, 台灣母公司名, 英文名, 泰交所代碼}
# 搜尋時以泰國當地名稱為主，同時涵蓋母公司名與英文名
COMPANY_MAP = {
    # --- PCB ---
    "泰達電": {"thai_cn": "泰達電", "tw_cn": "台達電", "en": "Delta Electronics Thailand", "set": "DELTA"},
    "泰鼎":   {"thai_cn": "泰鼎",   "tw_cn": "臻鼎",   "en": "Zhen Ding Technology",      "set": ""},
    "欣興":   {"thai_cn": "欣興",   "tw_cn": "欣興",   "en": "Unimicron",                  "set": ""},
    "華通":   {"thai_cn": "華通",   "tw_cn": "華通",   "en": "Compeq Manufacturing",        "set": ""},
    "金像電": {"thai_cn": "金像電", "tw_cn": "金像電", "en": "Gold Circuit Electronics",     "set": ""},
    "定穎":   {"thai_cn": "定穎",   "tw_cn": "定穎",   "en": "Dynamic Electronics",         "set": ""},
    "健鼎":   {"thai_cn": "健鼎",   "tw_cn": "健鼎",   "en": "Tripod Technology",            "set": ""},
    "燿華":   {"thai_cn": "燿華",   "tw_cn": "燿華",   "en": "Unitech PCB",                  "set": "UPCB"},
    "敬鵬":   {"thai_cn": "敬鵬",   "tw_cn": "敬鵬",   "en": "Chin-Poon Industrial",         "set": ""},
    "競國":   {"thai_cn": "競國",   "tw_cn": "競國",   "en": "Chin-Gou Electronic",           "set": ""},
    "高技":   {"thai_cn": "高技",   "tw_cn": "高技",   "en": "Kao Chi Enterprises",            "set": ""},
    # --- 伺服器/電子代工 ---
    "鴻海":   {"thai_cn": "鴻海",   "tw_cn": "鴻海",   "en": "Foxconn",                      "set": ""},
    "英業達": {"thai_cn": "英業達", "tw_cn": "英業達", "en": "Inventec",                      "set": ""},
    "廣達":   {"thai_cn": "廣達",   "tw_cn": "廣達",   "en": "Quanta Computer",               "set": ""},
    "群光":   {"thai_cn": "群光",   "tw_cn": "群光",   "en": "Chicony Electronics",            "set": ""},
    # --- 散熱 ---
    "雙鴻":   {"thai_cn": "泰鴻",   "tw_cn": "雙鴻",   "en": "Auras Technology",              "set": ""},
    "泰碩":   {"thai_cn": "泰碩",   "tw_cn": "泰碩",   "en": "Taisol Electronics",             "set": ""},
    # --- PCB 上游材料 ---
    "台虹":   {"thai_cn": "台虹",   "tw_cn": "台虹",   "en": "Taiflex Scientific",             "set": ""},
    "聯茂":   {"thai_cn": "聯茂",   "tw_cn": "聯茂",   "en": "Elite Material",                 "set": ""},
    "台燿":   {"thai_cn": "台燿",   "tw_cn": "台燿",   "en": "Taiwan Union Technology",        "set": ""},
}

# 向下相容：產生 VIP 查詢字串
VIP_COMPANIES_EN = [f'"{info["en"]}"' for info in COMPANY_MAP.values()]
VIP_COMPANIES_CN = [f'"{info["tw_cn"]}"' for info in COMPANY_MAP.values()]

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
        "pcb", "印刷電路板", "台商",
    ] + [name for info in COMPANY_MAP.values()
         for name in [info["thai_cn"], info["tw_cn"], info["en"]]],
}


def is_relevant(title, mode, custom_keyword=None):
    """檢查標題是否與搜尋模式相關（至少包含一個關鍵字）"""
    if mode == "company" and custom_keyword:
        # 個別台商：標題須含任一名稱變體
        title_lower = title.lower()
        info = COMPANY_MAP.get(custom_keyword, {})
        names = [
            info.get("thai_cn", ""), info.get("tw_cn", ""),
            info.get("en", ""), info.get("set", ""),
            custom_keyword,
        ]
        return any(n and n.lower() in title_lower for n in names)
    if mode == "custom" and custom_keyword:
        title_lower = title.lower()
        kw = custom_keyword.strip().lower()
        # 完整關鍵字比對
        if kw in title_lower:
            return True
        # 多詞比對：以空格拆分，每個詞都須出現（如 "Delta Electronics"）
        words = kw.split()
        if len(words) >= 2 and all(w in title_lower for w in words):
            return True
        # 中文逐字比對：僅對非 ASCII 字元拆分（如「泰達電」→「泰」「達」「電」）
        cjk_chars = [c for c in kw if ord(c) > 127]
        if len(cjk_chars) >= 2:
            matched = sum(1 for c in cjk_chars if c in title_lower)
            # 全部命中或至少超過一半（容許部分不符，如「泰達電」→「台達電」差一字）
            if matched >= len(cjk_chars) or (len(cjk_chars) >= 3 and matched >= len(cjk_chars) - 1):
                return True
        return False
    keywords = RELEVANCE_KEYWORDS.get(mode)
    if not keywords:
        return True
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in keywords)


def _build_query_templates(mode, custom_keyword=None):
    """
    依搜尋模式產生查詢模板列表。
    每個模板包含 name、query、hl/gl/ceid 參數，日期過濾由呼叫端填入。
    """
    templates = []

    if mode == "company" and custom_keyword:
        # 個別台商模式：泰國當地名 + 母公司名 + 英文名
        info = COMPANY_MAP.get(custom_keyword, {})
        thai_cn = info.get("thai_cn", custom_keyword)
        tw_cn = info.get("tw_cn", custom_keyword)
        en_name = info.get("en", custom_keyword)
        set_ticker = info.get("set", "")

        # 組合所有名稱變體（去重）
        cn_names = list(dict.fromkeys([thai_cn, tw_cn]))  # 保序去重
        cn_or = "+OR+".join(f"%22{n}%22" for n in cn_names)
        en_encoded = en_name.replace(" ", "+")

        # 中文查詢：泰國 + (泰達電 OR 台達電 OR "Delta Electronics Thailand")
        cn_query = f"泰國+{cn_or}+OR+%22{en_encoded}%22"
        # 英文查詢：Thailand + "Delta Electronics Thailand" OR 泰達電 OR 台達電
        en_query = f"Thailand+%22{en_encoded}%22+OR+{cn_or}"

        # 若有泰交所代碼，額外加入
        if set_ticker:
            cn_query += f"+OR+%22{set_ticker}%22"
            en_query += f"+OR+%22{set_ticker}%22"

        templates.extend([
            {"name": f"🏭 {custom_keyword} (中)", "query": cn_query,
             "hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"},
            {"name": f"🏭 {custom_keyword} (EN)", "query": en_query,
             "hl": "en-TH", "gl": "TH", "ceid": "TH:en"},
        ])
    elif mode == "custom" and custom_keyword:
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

    # 計算實際日期範圍，避免「1月」被誤解為「一月份」
    date_end = datetime.now().strftime('%Y-%m-%d')
    date_start = (datetime.now() - timedelta(days=days_int)).strftime('%Y-%m-%d')
    date_range_str = f"近 {days_label}（{date_start} ~ {date_end}）"

    if search_mode == "company":
        info = COMPANY_MAP.get(custom_keyword, {})
        en_name = info.get("en", custom_keyword)
        tw_cn = info.get("tw_cn", "")
        label_parts = [custom_keyword]
        if tw_cn and tw_cn != custom_keyword:
            label_parts.append(tw_cn)
        label_parts.append(en_name)
        topic_desc = f"{date_range_str} {'／'.join(label_parts)} 泰國動態"
    elif search_mode == "custom":
        topic_desc = f"關鍵字【{custom_keyword}】{date_range_str}"
    elif search_mode == "macro":
        topic_desc = f"{date_range_str} 泰國整體與台泰關係"
    elif search_mode == "industry":
        topic_desc = f"{date_range_str} 泰國 PCB 與電子製造"
    elif search_mode == "vip":
        topic_desc = f"{date_range_str} 泰國重點台商"

    output_text = f"""請扮演一位資深的「產業分析師」，分析【{topic_desc}】。

## 任務
1. 從以下新聞標題中，挑出 **10-15 則最重要的新聞**，說明為何重要
2. 歸納本期 **3-5 大關鍵趨勢**
3. 提出 **機會與風險** 評估
4. 如有特別重要的新聞需要深入了解，請自行上網搜尋該新聞的詳細內容

請用**繁體中文**，以 **Markdown** 條列式輸出，風格需專業且易讀。

========= 以下是新聞標題庫 ({datetime.now().strftime('%Y-%m-%d')}) =========
"""
    
    seen_titles = set()
    total_steps = len(sources)

    # 平行抓取 RSS（逐日拆分後請求數較多，提高併發數）
    max_workers = min(20, len(sources))
    status_text.text(f"📡 正在平行掃描 {len(sources)} 個來源（逐日拆分）...")

    # 按類別收集結果（去除日期後歸類）
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
                    if not is_relevant(entry.title, search_mode, custom_keyword):
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

    def _get_date_str(item):
        """取得文章的日期字串（YYYY-MM-DD），用於逐日分組"""
        try:
            return parsedate_to_datetime(item["date"]).strftime('%Y-%m-%d')
        except Exception:
            return "unknown"

    DAILY_PROMPT_LIMIT = 10  # 每天每類別最多放入 prompt 的篇數

    for category, entries in category_entries.items():
        # 依日期排序（新→舊）
        entries.sort(key=_sort_key, reverse=True)
        # 全部納入顯示與儲存
        news_items_for_json.extend(entries)

        output_text += f"\n## 【{category}】\n"
        if not entries:
            output_text += "(無相關新聞)\n"
            continue

        limit_per_day = DAILY_PROMPT_LIMIT

        # 依日期分組輸出純標題
        daily_count = {}
        current_day = None
        for item in entries:
            day = _get_date_str(item)
            daily_count.setdefault(day, 0)
            if daily_count[day] >= limit_per_day:
                continue
            daily_count[day] += 1
            if day != current_day:
                current_day = day
                output_text += f"\n### {day}\n"
            output_text += f"- [{item['source']}] {item['title']}\n"

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
        if 'last_company' not in st.session_state: st.session_state['last_company'] = None
        if 'active_source' not in st.session_state: st.session_state['active_source'] = None  # "topic" | "company" | "custom"

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
        
        # 偵測使用者切換了哪個選擇器（比對前次值）
        topic_changed = topic_selection and topic_selection != st.session_state.get('last_topic')

        # 3. 個別台商
        st.caption("3. 個別台商")
        try:
            company_selection = st.pills("Company", list(COMPANY_MAP.keys()), label_visibility="collapsed", selection_mode="single", key="pills_company")
        except AttributeError:
            company_selection = st.radio("Company", ["(請選擇)"] + list(COMPANY_MAP.keys()), label_visibility="collapsed")
            if company_selection == "(請選擇)": company_selection = None

        company_changed = company_selection and company_selection != st.session_state.get('last_company')

        # 優先處理最新的操作（避免 pills 殘留值互相覆蓋）
        if company_changed:
            st.session_state['last_company'] = company_selection
            st.session_state['active_source'] = "company"
            set_search("company", company_selection)
            st.rerun()
        elif topic_changed:
            st.session_state['last_topic'] = topic_selection
            st.session_state['active_source'] = "topic"
            set_search(TOPIC_MAP[topic_selection])
            st.rerun()

        # 4. 自訂搜尋
        st.caption("4. 關鍵字")
        def handle_custom_search():
            kw = st.session_state.kw_input
            if kw:
                st.session_state['active_source'] = "custom"
                st.session_state['last_topic'] = None
                st.session_state['last_company'] = None
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
                3. <b>重點台商</b>：鎖定 10 大指標台廠動態。<br>
                4. <b>個別台商</b>：單一台商中英文深度搜尋。
            </div>
            """, unsafe_allow_html=True)

        # 執行搜尋
        elif s_type == "company" and s_kw:
            info = COMPANY_MAP.get(s_kw, {})
            en_name = info.get("en", s_kw)
            with st.spinner(f"正在搜尋 {s_kw}（{en_name}）泰國動態..."):
                prompt, news_list = generate_chatgpt_prompt(selected_label, days_int, "company", s_kw)
                display_results(prompt, news_list)
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