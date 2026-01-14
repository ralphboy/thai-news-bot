import streamlit as st
import feedparser
import time
from datetime import datetime, timedelta
import json
import os

# ================= 頁面設定 =================
st.set_page_config(
    page_title="ThaiNews.Ai | 戰情室", 
    page_icon="🇹🇭", 
    layout="wide"
)

# ================= CSS 美化 =================
st.markdown("""
<style>
    .big-font { font-size: 32px !important; font-weight: 800; color: #1a1a1a; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    .stCode { border: 1px solid #d93025; }
</style>
""", unsafe_allow_html=True)

# ================= 爬蟲核心邏輯 (智慧切換版) =================

def get_rss_sources(days, custom_keyword=None):
    """
    智慧切換邏輯：
    1. 若有輸入自訂關鍵字 -> 只回傳該關鍵字的來源 (深度模式)
    2. 若無輸入 -> 回傳預設三大來源 (廣度模式)
    """
    sources = []
    
    # === 模式 A：深度鑽研 (只搜自訂) ===
    if custom_keyword and custom_keyword.strip():
        clean_keyword = custom_keyword.strip().replace(" ", "+")
        sources.append({
            "name": f"🔍 深度追蹤: {custom_keyword}",
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
    """根據模式生成對應的 Prompt"""
    status_text = st.empty() 
    progress_bar = st.progress(0)
    
    # 取得來源列表 (程式會自動判斷要拿哪一種)
    sources = get_rss_sources(days_int, custom_keyword)
    
    # === 動態生成 AI 指令 (根據是否有關鍵字) ===
    if custom_keyword and custom_keyword.strip():
        # [指令 A] 針對特定主題分析
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
        # [指令 B] 原本的三大方向分析
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

    # 組合最終 Prompt
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
                # 自訂模式抓多一點(30)，預設模式抓適量(15-20)
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
    status_text.text("✅ 抓取完成！請點擊下方區塊右上角的複製按鈕。")
    time.sleep(1)
    status_text.empty()
    progress_bar.empty()
    
    return output_text

# ================= 網頁主程式 =================

st.markdown('<div class="big-font">ThaiNews.Ai 🇹🇭 戰情室</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🤖 ChatGPT 懶人包 (生成器)", "📊 歷史新聞庫"])

# --- Tab 1 ---
with tab1:
    st.markdown("### 🚀 一鍵生成 ChatGPT 分析指令")
    
    # 1. 時間選擇
    st.write("請選擇新聞抓取區間：")
    time_options = {
        "1 天 (24h)": 1,
        "3 天": 3,
        "1 週 (7天)": 7,
        "2 週 (14天)": 14,
        "1 個月 (30天)": 30
    }
    selected_label = st.radio(
        "選擇區間",
        options=list(time_options.keys()),
        horizontal=True,
        label_visibility="collapsed"
    )
    days_int = time_options[selected_label]

    # 2. 自訂搜尋關鍵字
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        custom_keyword = st.text_input(
            "🔍 自訂搜尋關鍵字 (選填)", 
            placeholder="例如: \"Delta Electronics\" -Airline"
        )
    with col2:
        st.write("") 
        st.caption("⚠️ 若輸入此欄位，系統將**只搜尋此關鍵字**，不抓取預設的三大類別。")

    st.markdown("---")
    
    # 按鈕文字會根據模式改變
    btn_text = f"開始搜尋: {custom_keyword}" if custom_keyword else f"開始抓取預設三大新聞 ({selected_label})"
    
    if st.button(btn_text, type="primary"):
        with st.spinner(f"正在全網搜索..."):
            prompt_content = generate_chatgpt_prompt(selected_label, days_int, custom_keyword)
            st.success("🎉 生成成功！")
            st.code(prompt_content, language="markdown")

# --- Tab 2 ---
with tab2:
    st.markdown("### 📂 本地資料庫檢視")
    if os.path.exists('news_data.json'):
        with open('news_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        st.write(f"上次更新: {data.get('timestamp', '未知')}")
        st.json(data.get('news_list', []))
    else:
        st.warning("目前沒有歷史存檔。")
