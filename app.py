import streamlit as st
import feedparser
import time
from datetime import datetime, timedelta
import json
import os

# ================= 1. 頁面全域設定 =================
st.set_page_config(
    page_title="ThaiNews.Ai | 戰情室", 
    page_icon="🇹🇭", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= 2. UI/UX Pro Max - CSS 魔改區 =================
st.markdown("""
<style>
    /* 引入 Google Fonts: Inter (現代科技感字體) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    /* 全站基礎設定：深藍儀表板背景 */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #020617; /* 深夜藍 */
        color: #e5e7eb;
    }

    /* 頂部 Header 漸層背景卡片：深藍 x 泰皇金 */
    .header-container {
        background: radial-gradient(circle at top left, #fbbf24 0%, #0f172a 45%, #020617 100%);
        padding: 32px 30px;
        border-radius: 18px;
        color: #f9fafb;
        box-shadow: 0 18px 45px rgba(0,0,0,0.6);
        margin-bottom: 26px;
        border: 1px solid rgba(248, 250, 252, 0.08);
    }
    .header-title {
        font-size: 40px;
        font-weight: 800;
        margin: 0;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        background: linear-gradient(to right, #fef9c3, #facc15, #eab308);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .header-subtitle {
        font-size: 15px;
        color: #c7d2fe;
        margin-top: 10px;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }

    /* 主操作卡片：深藍玻璃卡片 */
    .control-card {
        background: radial-gradient(circle at top left, rgba(248, 250, 252, 0.04), rgba(15, 23, 42, 0.96));
        padding: 24px 26px;
        border-radius: 18px;
        box-shadow: 0 16px 40px rgba(0,0,0,0.7);
        border: 1px solid rgba(148, 163, 184, 0.45);
        margin-bottom: 25px;
        backdrop-filter: blur(18px);
    }

    /* 自訂輸入框美化：深藍邊框 + 金色聚焦 */
    .stTextInput > div > div > input {
        border-radius: 999px;
        border: 1px solid rgba(148, 163, 184, 0.6);
        background-color: rgba(15, 23, 42, 0.85);
        padding: 10px 18px;
        font-size: 15px;
        color: #e5e7eb;
        transition: all 0.2s ease;
    }
    .stTextInput > div > div > input::placeholder {
        color: rgba(148, 163, 184, 0.8);
    }
    .stTextInput > div > div > input:focus {
        border-color: #facc15;
        box-shadow: 0 0 0 1px rgba(250, 204, 21, 0.65);
    }

    /* Pro Max 按鈕：深藍 x 金色 */
    .stButton > button {
        background: linear-gradient(135deg, #0f172a 0%, #1d283a 35%, #facc15 100%);
        color: #020617;
        border: none;
        padding: 12px 24px;
        border-radius: 999px;
        font-weight: 700;
        font-size: 15px;
        width: 100%;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        box-shadow: 0 14px 32px rgba(15, 23, 42, 0.9);
        transition: transform 0.08s ease-out, box-shadow 0.15s ease-out, filter 0.15s ease-out;
    }
    .stButton > button:hover {
        filter: brightness(1.08);
        box-shadow: 0 18px 40px rgba(15, 23, 42, 1);
        transform: translateY(-1px);
        color: #020617;
    }
    .stButton > button:active {
        transform: translateY(1px);
        box-shadow: 0 10px 20px rgba(15, 23, 42, 0.9);
    }

    /* Radio Button 儀表板膠囊樣式 */
    .stRadio > div {
        background: rgba(15, 23, 42, 0.9);
        padding: 10px;
        border-radius: 999px;
        display: flex;
        justify-content: space-between;
        border: 1px solid rgba(148, 163, 184, 0.7);
    }

    /* st.metric 儀表板卡片樣式 */
    div[data-testid="stMetric"] {
        background: radial-gradient(circle at top left, rgba(250, 204, 21, 0.22), rgba(15, 23, 42, 0.98));
        padding: 16px 18px;
        border-radius: 16px;
        border: 1px solid rgba(250, 204, 21, 0.55);
        box-shadow: 0 16px 40px rgba(0,0,0,0.8);
        color: #e5e7eb;
    }
    div[data-testid="stMetric"] > label {
        color: rgba(226, 232, 240, 0.9);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
    }
    div[data-testid="stMetric"] > div {
        color: #facc15;
        font-size: 1.4rem;
        font-weight: 800;
    }

    /* 結果代碼區塊美化：深藍框 + 光暈 */
    .stCode {
        border-radius: 16px;
        border: 1px solid rgba(148, 163, 184, 0.6);
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.95);
        background-color: #020617;
    }

    /* 新聞卡片樣式：深藍卡片 + 金色左框 */
    .news-card {
        background: radial-gradient(circle at top left, rgba(15, 23, 42, 0.9), rgba(15, 23, 42, 1));
        padding: 18px 20px;
        margin-bottom: 14px;
        border-radius: 14px;
        border-left: 4px solid #facc15;
        box-shadow: 0 14px 30px rgba(0,0,0,0.8);
        transition: transform 0.18s ease-out, border-color 0.18s ease-out, box-shadow 0.18s ease-out;
    }
    .news-card:hover {
        transform: translateX(4px) translateY(-1px);
        border-left-color: #fde68a;
        box-shadow: 0 18px 40px rgba(0,0,0,1);
    }
    .news-date { font-size: 11px; color: #9ca3af; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.12em; }
    .news-source { font-weight: 700; color: #facc15; font-size: 12px; }
    .news-title { font-size: 17px; font-weight: 600; color: #e5e7eb; text-decoration: none; display:block; margin-top:4px;}
    .news-title:hover { color: #fde68a; text-decoration: underline; }

    /* 隱藏預設 Footer / MainMenu */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# ================= 3. 爬蟲核心邏輯 =================

def get_rss_sources(days, custom_keyword=None):
    sources = []
    
    # === 模式 A：深度鑽研 (只搜自訂) ===
    if custom_keyword and custom_keyword.strip():
        # 自動補上 Thailand 以避免抓到無關公司 (如 Delta Airlines)
        # 除非使用者已經打在裡面了
        search_term = custom_keyword.strip()
        
        clean_keyword = search_term.replace(" ", "+")
        sources.append({
            "name": f"🔍 深度追蹤: {search_term}",
            "url": f"https://news.google.com/rss/search?q={clean_keyword}+when:{days}d&hl=en-TH&gl=TH&ceid=TH:en"
        })
        return sources

    # === 模式 B：廣度掃描 (預設三大類) ===
    sources.extend([
        {
            "name": "🇹🇭 1. 泰國整體重要新聞", 
            "url": f"https://news.google.com/rss/search?q=Thailand+when:{days}d&hl=en-TH&gl=TH&ceid=TH:en"
        },
        {
            "name": "🔌 2. PCB 與電子製造", 
            "url": f"https://news.google.com/rss/search?q=Thailand+PCB+OR+%22Printed+Circuit+Board%22+OR+%22Electronics+Manufacturing%22+OR+%22Server+Production%22+when:{days}d&hl=en-TH&gl=TH&ceid=TH:en"
        },
        {
            "name": "🇹🇼 3. 台泰關係", 
            "url": f"https://news.google.com/rss/search?q=Thailand+Taiwan+OR+%22Taiwanese+investment%22+OR+%22Taiwan+companies%22+OR+%22Trade+Relations%22+when:{days}d&hl=en-TH&gl=TH&ceid=TH:en"
        }
    ])
    return sources

def generate_chatgpt_prompt(days_label, days_int, custom_keyword):
    status_text = st.empty() 
    progress_bar = st.progress(0)
    
    sources = get_rss_sources(days_int, custom_keyword)
    
    # 動態生成 Prompt
    if custom_keyword and custom_keyword.strip():
        instruction_prompt = f"""
請扮演一位資深的「產業分析師」。
以下是我針對關鍵字【{custom_keyword}】抓取的{days_label}新聞資料。

請閱讀這些新聞，幫我撰寫一份「深度主題分析報告」：

### 1. 🔍 重點摘要 (Executive Summary)
   - 請總結關於「{custom_keyword}」發生的最重要事件。

### 2. 📈 市場與商業影響
   - 這些新聞對該公司或該產業的供應鏈有何具體影響？
   - 是否有擴廠、併購、或政策變動的訊號？

### 3. ⚠️ 潛在機會與風險
   - 對於投資者或競爭對手來說，有什麼值得注意的機會或風險？

(若新聞內容與該關鍵字關聯度低，請明確指出「雜訊過多，無實質進展」。)
"""
    else:
        instruction_prompt = f"""
請扮演一位資深的「東南亞產經分析師」。
以下是我透過程式抓取的【{days_label} 泰國 PCB 與電子產業新聞資料庫】。

請閱讀這些新聞，幫我按照以下方向進行「深度整理與分析」：

### 1. 🇹🇭 泰國整體重要新聞
   - 重點關注：政治動態、重大經濟政策、社會安全。
   - 列出最具影響力的 3-5 件大事。

### 2. 🔌 泰國 PCB 與電子製造
   - 重點關注：新廠設立、供應鏈移轉、大型投資案。
   - 分析對全球供應鏈的意義。

### 3. 🇹🇼 台泰關係與台商動態
   - 重點關注：台灣企業投資、雙邊貿易、地緣政治。
   - 指出台商的機會與風險。
"""

    output_text = f"""
{instruction_prompt}

請用**繁體中文**，並以 **Markdown** 條列式輸出，風格需專業且易讀。

========= 以下是新聞資料庫 ({datetime.now().strftime('%Y-%m-%d')}) =========
"""
    
    seen_titles = set()
    total_steps = len(sources)
    
    for i, source in enumerate(sources):
        status_text.text(f"📡 正在掃描: {source['name']} ...")
        
        try:
            feed = feedparser.parse(source['url'])
            
            if len(feed.entries) > 0:
                output_text += f"\n## 【{source['name']}】\n"
                limit = 30 if custom_keyword else (15 if days_int <= 3 else 25)
                
                for entry in feed.entries[:limit]: 
                    if entry.title in seen_titles: continue
                    seen_titles.add(entry.title)
                    
                    source_name = entry.source.title if 'source' in entry else "Google News"
                    pub_date = entry.published if 'published' in entry else ""
                    output_text += f"- [{pub_date}] [{source_name}] {entry.title}\n  連結: {entry.link}\n"
            else:
                output_text += f"\n## 【{source['name']}】\n(無相關新聞)\n"

        except Exception as e:
            st.error(f"抓取錯誤: {e}")
        
        progress_bar.progress((i + 1) / total_steps)
        time.sleep(0.5)

    output_text += "\n========= 資料結束 ========="
    status_text.success("✅ 抓取完成！請點擊下方區塊右上角的複製按鈕。")
    time.sleep(1)
    status_text.empty()
    progress_bar.empty()
    
    return output_text

# ================= 4. 網頁主程式 (UI 佈局) =================

# --- Header 區塊 ---
st.markdown("""
<div class="header-container">
    <p class="header-title">ThaiNews.Ai 🇹🇭 戰情室</p>
    <p class="header-subtitle">AI 驅動的泰國電子產業與台商動態追蹤系統</p>
</div>
""", unsafe_allow_html=True)

# 建立分頁
tab1, tab2 = st.tabs(["🤖 ChatGPT 懶人包 (生成器)", "📊 歷史新聞庫"])

# --- Tab 1: 生成器 ---
with tab1:
    # 使用 Container 建立白色卡片區塊
    with st.container():
        st.markdown('<div class="control-card">', unsafe_allow_html=True)
        st.markdown("### 🎯 戰情儀表板設定")
        
        # 1. 兩欄排版：左側輸入、右側說明
        left_col, right_col = st.columns([2, 1])
        with left_col:
            custom_keyword = st.text_input(
                "🔍 自訂搜尋關鍵字 (選填，輸入英文公司名)", 
                placeholder='例如: "Delta Electronics" Thailand, CP Group...',
                help="若輸入此欄，系統將切換為「深度鑽研模式」，只搜尋此關鍵字。"
            )
        with right_col:
            st.markdown(
                "##### 戰情模式說明\n"
                "- 未輸入時：系統自動進行 **泰國整體 + PCB + 台泰關係** 的廣度掃描。\n"
                "- 有輸入關鍵字：啟用 **深度鑽研模式**，專注追蹤單一主題。"
            )
        
        # 2. 時間選擇
        st.write("⏱️ 選擇時間區間：")
        time_options = {
            "24H (快訊)": 1,
            "3 天": 3,
            "1 週": 7,
            "2 週": 14,
            "1 個月": 30
        }
        
        selected_label = st.radio(
            "選擇區間",
            options=list(time_options.keys()),
            horizontal=True,
            label_visibility="collapsed"
        )
        days_int = time_options[selected_label]

        # 3. 儀表板指標列（使用 st.columns + st.metric）
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        with metric_col1:
            st.metric("模式", "深度鑽研" if custom_keyword else "廣度掃描")
        with metric_col2:
            st.metric("時間範圍", selected_label)
        with metric_col3:
            st.metric("搜尋來源數", len(get_rss_sources(days_int, custom_keyword)))
        
        st.markdown("<br>", unsafe_allow_html=True)  # 增加一點間距

        # 4. 動態按鈕文字
        btn_text = f"🚀 啟動 AI 戰情搜索 (目標: {custom_keyword})" if custom_keyword else f"🚀 啟動全網掃描 (範圍: {selected_label})"
        
        # 5. 執行按鈕
        if st.button(btn_text, type="primary"):
            st.markdown('</div>', unsafe_allow_html=True) # 結束卡片 div
            
            # 開始執行 (這部分會顯示在卡片下方)
            with st.spinner(f"正在連線 Google News 全球節點..."):
                prompt_content = generate_chatgpt_prompt(selected_label, days_int, custom_keyword)
                
                # 結果顯示區
                st.markdown("### ✅ 生成結果 (請點擊右上角複製)")
                st.code(prompt_content, language="markdown")
        else:
            st.markdown('</div>', unsafe_allow_html=True) # 結束卡片 div

# --- Tab 2: 歷史資料 ---
with tab2:
    if os.path.exists('news_data.json'):
        with open('news_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        st.markdown(f"**上次更新時間:** {data.get('timestamp', '未知')}")
        
        # 把 JSON 轉成漂亮的卡片列表
        news_list = data.get('news_list', [])
        for news in news_list:
            title = news.get('title')
            link = news.get('link')
            source = news.get('source')
            date = news.get('date')
            
            st.markdown(f"""
            <div class="news-card">
                <div class="news-date">{date} • {source}</div>
                <a href="{link}" target="_blank" class="news-title">{title}</a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📂 目前沒有本地歷史存檔，請先執行搜尋。")

# 底部版權宣告
st.markdown("""
<div style="text-align: center; color: #aaa; padding: 20px; font-size: 12px;">
    Powered by Google News & OpenAI • Design by UI/UX Pro Max
</div>
""", unsafe_allow_html=True)
