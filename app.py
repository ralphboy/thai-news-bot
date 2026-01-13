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
    /* 讓複製區塊明顯一點 */
    .stCode { border: 1px solid #d93025; }
</style>
""", unsafe_allow_html=True)

# ================= 爬蟲核心邏輯 (動態時間版) =================

def get_rss_sources(days):
    """
    根據使用者選擇的天數，動態生成 RSS 連結
    search?q=... when:{days}d ...
    """
    return [
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
    ]

def generate_chatgpt_prompt(days_label, days_int):
    """抓取新聞並生成 Prompt"""
    status_text = st.empty() 
    progress_bar = st.progress(0)
    
    # 取得動態來源列表
    sources = get_rss_sources(days_int)
    
    output_text = f"""
請扮演一位資深的「東南亞產經分析師」。
以下是我透過程式抓取的【{days_label} 泰國 PCB 與電子產業新聞資料庫】。

請閱讀這些新聞標題與來源，幫我按照以下三個方向進行「深度整理與分析」：

### 1. 🇹🇭 泰國整體重要新聞
   - 重點關注：政治動態、重大經濟政策、社會安全。
   - 請列出最具影響力的 3-5 件大事。

### 2. 🔌 泰國 PCB 與電子製造
   - 重點關注：新廠設立（特別是 PCB 廠）、供應鏈移轉動態、大型投資案。
   - 分析這對全球電子供應鏈的意義。

### 3. 🇹🇼 台泰關係與台商動態
   - 重點關注：台灣企業投資、雙邊貿易、地緣政治影響。
   - 指出台商的機會與風險。

請用**繁體中文**，並以 **Markdown** 條列式輸出，風格需專業且易讀。
若某個分類下無重大新聞，請註明「該期間無相關報導」。

========= 以下是 {days_label} 新聞資料庫 ({datetime.now().strftime('%Y-%m-%d')}) =========
"""
    
    seen_titles = set()
    total_steps = len(sources)
    
    for i, source in enumerate(sources):
        status_text.text(f"📡 正在掃描 ({days_label}): {source['name']} ...")
        
        # 增加容錯機制
        try:
            feed = feedparser.parse(source['url'])
            
            if len(feed.entries) > 0:
                output_text += f"\n## 【{source['name']}】\n"
                # 依據天數調整抓取數量：天數少抓少一點(15則)，天數多抓多一點(30則)
                limit = 15 if days_int <= 3 else 30
                
                for entry in feed.entries[:limit]: 
                    if entry.title in seen_titles: continue
                    seen_titles.add(entry.title)
                    
                    source_name = entry.source.title if 'source' in entry else "Google News"
                    pub_date = entry.published if 'published' in entry else ""
                    # 格式：[日期] [媒體] 標題
                    output_text += f"- [{pub_date}] [{source_name}] {entry.title}\n  連結: {entry.link}\n"
        except Exception as e:
            st.error(f"抓取錯誤: {e}")
        
        # 更新進度條
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

# 建立分頁
tab1, tab2 = st.tabs(["🤖 ChatGPT 懶人包 (生成器)", "📊 歷史新聞庫"])

# --- Tab 1: ChatGPT 懶人包生成器 ---
with tab1:
    st.markdown("### 🚀 一鍵生成 ChatGPT 分析指令")
    
    # === 新增功能：時間選擇區 ===
    st.write("請選擇新聞抓取區間：")
    
    # 定義選項與對應的天數數值
    time_options = {
        "1 天 (24h)": 1,
        "3 天": 3,
        "1 週 (7天)": 7,
        "2 週 (14天)": 14,
        "1 個月 (30天)": 30
    }
    
    # 使用橫向單選按鈕 (Radio Button)
    selected_label = st.radio(
        "選擇區間",
        options=list(time_options.keys()),
        horizontal=True,
        label_visibility="collapsed"
    )
    
    # 取得對應的天數整數
    days_int = time_options[selected_label]

    st.info(f"準備抓取 **「過去 {selected_label}」** 的泰國產業新聞...")
    
    # 按鈕觸發
    if st.button(f"開始抓取 ({selected_label})", type="primary"):
        with st.spinner(f"正在連線至 Google News (範圍: {selected_label})..."):
            prompt_content = generate_chatgpt_prompt(selected_label, days_int)
            
            st.success("🎉 生成成功！")
            st.markdown("請點擊下方黑色區塊**右上角的 📄 小圖示**，即可全選複製，然後貼給 ChatGPT。")
            
            st.code(prompt_content, language="markdown")

# --- Tab 2: 歷史新聞庫 ---
with tab2:
    st.markdown("### 📂 本地資料庫檢視")
    if os.path.exists('news_data.json'):
        with open('news_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        st.write(f"上次更新: {data.get('timestamp', '未知')}")
        st.json(data.get('news_list', []))
    else:
        st.warning("目前沒有歷史存檔。")
