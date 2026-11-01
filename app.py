import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime

# ================= 1. 移动端原生视口与主题注入 =================
st.set_page_config(
    page_title="ReasonVest Pro - 全美股全维决策终端",
    page_icon="🧭",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    .mobile-card {
        background: #181b26;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 12px;
        border: 1px solid #282d3f;
    }
    .grid-pill {
        background: #21262d;
        border-radius: 8px;
        padding: 8px 12px;
        margin-bottom: 8px;
        border-left: 3px solid #58a6ff;
    }
    .news-badge {
        background: #21262d;
        color: #8b949e;
        font-size: 11px;
        padding: 2px 6px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ================= 2. 股票底层数据池（主界面 20 大核心股 + 潜力股 + 各类型细分赛道） =================
CURATED_POOLS = {
    "👑 20大核心巨头 (20只)": [
        {"ticker": "NVDA", "name": "英伟达", "tag": "芯片/AI算力"},
        {"ticker": "AAPL", "name": "苹果", "tag": "消费电子/端侧AI"},
        {"ticker": "MSFT", "name": "微软", "tag": "云/企业AI"},
        {"ticker": "AMZN", "name": "亚马逊", "tag": "电商/AWS云"},
        {"ticker": "GOOGL", "name": "谷歌", "tag": "搜索/AI模型"},
        {"ticker": "META", "name": "Meta", "tag": "社交/元宇宙"},
        {"ticker": "TSLA", "name": "特斯拉", "tag": "自动驾驶/机器人"},
        {"ticker": "BRK-B", "name": "伯克希尔", "tag": "巴菲特全能控股"},
        {"ticker": "AVGO", "name": "博通", "tag": "网络与定制ASIC"},
        {"ticker": "LLY", "name": "礼来", "tag": "减重药GLP-1"},
        {"ticker": "JPM", "name": "摩根大通", "tag": "华尔街银行龙头"},
        {"ticker": "WMT", "name": "沃尔玛", "tag": "全美零售之王"},
        {"ticker": "V", "name": "Visa", "tag": "全球支付结算网络"},
        {"ticker": "XOM", "name": "埃克森美孚", "tag": "传统能源龙头"},
        {"ticker": "MA", "name": "万事达", "tag": "数字支付网络"},
        {"ticker": "UNH", "name": "联合健康", "tag": "全美最大健康医疗"},
        {"ticker": "COST", "name": "好市多", "tag": "会员制量贩仓储"},
        {"ticker": "ORCL", "name": "甲骨文", "tag": "数据库与云算力"},
        {"ticker": "HD", "name": "家得宝", "tag": "家装零售龙头"},
        {"ticker": "PG", "name": "宝洁", "tag": "日常必需消费龙头"}
    ],
    "🔥 爆发潜力黑马": [
        {"ticker": "APP", "name": "AppLovin", "tag": "AI广告引擎/高增长"},
        {"ticker": "PLTR", "name": "Palantir", "tag": "政企级AI操作系统"},
        {"ticker": "RKLB", "name": "Rocket Lab", "tag": "商业航天发射先驱"},
        {"ticker": "SYM", "name": "Symbotic", "tag": "智能AI仓储机器人"},
        {"ticker": "VKTX", "name": "Viking", "tag": "小分子减重药黑马"},
        {"ticker": "SOFI", "name": "SoFi Tech", "tag": "数字新一代银行"},
        {"ticker": "IONQ", "name": "IonQ", "tag": "离子阱量子计算前沿"},
        {"ticker": "SOUN", "name": "SoundHound", "tag": "车载/餐饮语音AI"},
        {"ticker": "TEM", "name": "Tempus AI", "tag": "医疗基因大数据AI"},
        {"ticker": "HIMS", "name": "Hims & Hers", "tag": "远程个性化医疗黑马"}
    ],
    "💻 科技与芯片": [
        {"ticker": "AMD", "name": "超威半导体", "tag": "数据中心GPU/CPU"},
        {"ticker": "TSM", "name": "台积电", "tag": "全球先进制程代工"},
        {"ticker": "QCOM", "name": "高通", "tag": "智能手机与车规芯片"},
        {"ticker": "ASML", "name": "阿斯麦", "tag": "EUV极紫外光刻机"},
        {"ticker": "ARM", "name": "Arm架构", "tag": "低功耗芯片IP授权"},
        {"ticker": "MU", "name": "美光科技", "tag": "HBM高带宽存储内存"}
    ],
    "⚡ AI能源与基建": [
        {"ticker": "VST", "name": "Vistra", "tag": "数据中心核电直供电"},
        {"ticker": "CEG", "name": "Constellation", "tag": "清洁核电基建龙头"},
        {"ticker": "CCJ", "name": "Cameco", "tag": "全球核燃料铀矿开采"},
        {"ticker": "NEE", "name": "新纪元能源", "tag": "全美最大绿色公用事业"}
    ],
    "💊 生物医疗创新": [
        {"ticker": "CRSP", "name": "CRISPR", "tag": "诺奖基因编辑疗法"},
        {"ticker": "ISRG", "name": "直觉外科", "tag": "达芬奇手术机器人"},
        {"ticker": "MRNA", "name": "Moderna", "tag": "mRNA肿瘤疫苗先驱"},
        {"ticker": "REGN", "name": "再生元", "tag": "眼科与单抗新药"}
    ],
    "🛡️ 军工与高端制造": [
        {"ticker": "LMT", "name": "洛克希德马丁", "tag": "F-35与导弹防务"},
        {"ticker": "GE", "name": "GE航空航天", "tag": "商用与军用航发龙头"},
        {"ticker": "RTX", "name": "雷神技术", "tag": "雷达探测与防御系统"}
    ]
}

# ================= 3. SEC 全美股官方 8000+ 标的全量字典 =================
@st.cache_data(ttl=86400)
def load_all_sec_us_stocks():
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {"User-Agent": "ReasonVestApp InvestmentResearch/1.0 (contact@reasonvest.com)"}
    stock_list = []
    try:
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            for item in data.values():
                t = str(item['ticker']).upper().replace(".", "-")
                name = item['title'].title()
                stock_list.append({"ticker": t, "name": name, "label": f"{t} | {name}"})
    except Exception:
        pass

    if not stock_list:
        fallback = [
            ("NVDA", "Nvidia Corp"), ("AAPL", "Apple Inc"), ("MSFT", "Microsoft Corp"), 
            ("AMZN", "Amazon Com Inc"), ("GOOGL", "Alphabet Inc"), ("META", "Meta Platforms"),
            ("TSLA", "Tesla Inc"), ("NFLX", "Netflix Inc"), ("NKE", "Nike Inc"),
            ("NIO", "Nio Inc"), ("AMD", "Advanced Micro Devices"), ("AVGO", "Broadcom Inc")
        ]
        for t, n in fallback:
            stock_list.append({"ticker": t, "name": n, "label": f"{t} | {n}"})
    
    stock_list.sort(key=lambda x: x["ticker"])
    return stock_list

# ================= 4. 极速行情与资讯抓取 =================
@st.cache_data(ttl=120)
def fetch_batch_page_quotes(ticker_list):
    results = []
    for t in ticker_list:
        try:
            fi = yf.Ticker(t).fast_info
            price = fi.last_price or 0.0
            prev = fi.previous_close or price
            pct = ((price - prev) / prev * 100) if prev else 0.0
            results.append({
                "Ticker": t,
                "现价($)": round(float(price), 2),
                "涨跌幅": f"{pct:+.2f}%",
                "_pct_num": pct
            })
        except:
            results.append({
                "Ticker": t,
                "现价($)": "N/A",
                "涨跌幅": "0.00%",
                "_pct_num": 0.0
            })
    return pd.DataFrame(results)

@st.cache_data(ttl=300)
def fetch_pool_metrics(pool_name):
    items = CURATED_POOLS.get(pool_name, [])
    results = []
    for s in items:
        t = s["ticker"]
        try:
            info = yf.Ticker(t).info
            rev_growth = info.get("revenueGrowth", 0) or 0
            gross_margin = info.get("grossMargins", 0) or 0
            pe = info.get("forwardPE", 0) or 0
            price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
            mcap = (info.get("marketCap", 0) or 0) / 1e9

            results.append({
                "Ticker": t,
                "公司名称": s["name"],
                "核心业务": s["tag"],
                "现价($)": round(price, 2),
                "营收增速": f"{rev_growth * 100:.1f}%",
                "毛利率": f"{gross_margin * 100:.1f}%",
                "前瞻PE": round(pe, 1) if pe else "N/A",
                "市值(B)": round(mcap, 1)
            })
        except:
            continue
    return pd.DataFrame(results)

@st.cache_data(ttl=300)
def fetch_global_macro():
    try:
        vix = yf.Ticker('^VIX').history(period='2d')['Close'].iloc[-1]
    except:
        vix = 18.5
    try:
        tnx = yf.Ticker('^TNX').history(period='2d')['Close'].iloc[-1]
    except:
        tnx = 4.25
    return round(float(vix), 1), round(float(tnx), 2)

@st.cache_data(ttl=180)
def fetch_single_stock_all(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info or {}
    try:
        hist = stock.history(period="1y")
    except:
        hist = pd.DataFrame()

    insider_status = "⚪ 内部筹码平稳"
    try:
        insiders = stock.insider_transactions
        if insiders is not None and not insiders.empty:
            texts = insiders['Text'].astype(str).str.lower()
            buys = texts.str.contains('buy|purchase').sum()
            sales = texts.str.contains('sale|sold').sum()
            if buys > sales:
                insider_status = "🟢 高管净增持 (信心强烈)"
            elif sales > buys * 2:
                insider_status = "🔴 高管持续减持 (需警惕)"
    except:
        pass

    beat_rate = "75% (8战6胜)"
    try:
        ed = stock.earnings_dates
        if ed is not None and not ed.empty and 'Surprise(%)' in ed.columns:
            recent = ed.dropna(subset=['Surprise(%)']).head(8)
            if not recent.empty:
                beats = (recent['Surprise(%)'] > 0).sum()
                total = len(recent)
                beat_rate = f"{int(beats/total*100)}% ({total}战{beats}胜)"
    except:
        pass

    try:
        stock_news = stock.news or []
    except:
        stock_news = []

    return info, hist, insider_status, beat_rate, stock_news

# ================= 5. 全维量化推理大脑 =================
def run_master_evaluation(info, hist, c_price, vix, tnx, insider_status, beat_rate):
    rev_growth = info.get("revenueGrowth", 0) or 0
    gross_margin = info.get("grossMargins", 0) or 0
    pe = info.get("forwardPE", 0) or 0
    target_median = info.get("targetMedianPrice", c_price) or c_price
    fifty_low = info.get("fiftyTwoWeekLow", c_price * 0.75) or (c_price * 0.75)
    upside_pct = ((target_median - c_price) / c_price * 100) if c_price else 0

    pe_percentile = 50.0
    trailing_eps = info.get('trailingEps') or 0
    if trailing_eps > 0 and not hist.empty and len(hist) > 30:
        pe_series = hist['Close'] / trailing_eps
        cur_calc_pe = c_price / trailing_eps
        pe_percentile = round(float((pe_series < cur_calc_pe).mean() * 100), 1)

    rsi_val = 50.0
    sma_50 = c_price
    if not hist.empty and len(hist) >= 15:
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        rsi_series = 100 - (100 / (1 + rs))
        rsi_val = round(float(rsi_series.iloc[-1]), 1) if not pd.isna(rsi_series.iloc[-1]) else 50.0
        if len(hist) >= 50:
            sma_50 = round(float(hist['Close'].rolling(50).mean().iloc[-1]), 2)

    score = 50
    if rev_growth > 0.25: score += 15
    elif rev_growth > 0.10: score += 8
    elif rev_growth < 0: score -= 15

    if gross_margin > 0.50: score += 10
    elif gross_margin < 0.20: score -= 10

    if pe_percentile < 30: score += 10
    elif pe_percentile > 80: score -= 12

    if upside_pct > 20: score += 10
    elif upside_pct < 0: score -= 10

    if vix > 28: score -= 8
    elif vix < 15: score += 5

    if "增持" in insider_status: score += 8
    elif "减持" in insider_status: score -= 6

    if score >= 75:
        verdict = "强烈推荐"
        short_bias = "看涨 🚀"
        horizon_desc = f"基本面健康扩张，估值处于合理水温，分析师目标空间达 {upside_pct:+.1f}%，短期共振偏多。"
    elif score >= 60:
        verdict = "逢低买入"
        short_bias = "看涨 🚀"
        horizon_desc = "质地优良，具备良好的安全边际，短期处于震荡偏多上行通道。"
    elif score >= 45:
        verdict = "谨慎观望"
        short_bias = "中性震荡 ⚖️"
        horizon_desc = "估值分位数偏高或短期缺乏超预期事件催化，建议等待充分回调。"
    else:
        verdict = "建议规避"
        short_bias = "看跌 📉"
        horizon_desc = "估值面临压缩风险或筹码松动，短期下行修正风险未出尽。"

    ideal_lower = max(fifty_low, c_price * 0.88)
    ideal_upper = min(c_price * 0.96, (sma_50 if sma_50 > 0 else c_price))
    if ideal_upper <= ideal_lower:
        ideal_upper = c_price * 0.98
        ideal_lower = c_price * 0.90
    stop_loss = round(ideal_lower * 0.94, 2)

    pros = [
        f"**业绩成长动力**：最新季度营收增速 **{rev_growth*100:.1f}%**，毛利率 **{gross_margin*100:.1f}%**。",
        f"**机构目标上行空间**：华尔街一致预期目标价 **${target_median:.2f}** (潜在空间 **{upside_pct:+.1f}%**)。",
        f"**财报与筹码验证**：历史财报击败率 **{beat_rate}**，高管交易显示【{insider_status}】。"
    ]

    cons = [
        f"**历史估值分位水位**：目前处于近一年历史估值的 **{pe_percentile:.1f}%** 分位点 (前瞻PE: {pe:.1f}x)。",
        f"**宏观无风险利率承压**：10年期美债收益率为 **{tnx}%**，对高估值科技标的估值存在压制作用。",
        f"**技术面超买风险**：当前 RSI(14) 为 **{rsi_val}**，高于 70 切忌盲目追高，需等待回调挂单。"
    ]

    return {
        "score": min(98, max(20, score)),
        "verdict": verdict,
        "short_bias": short_bias,
        "horizon_desc": horizon_desc,
        "pe_percentile": pe_percentile,
        "rsi_val": rsi_val,
        "buy_zone": f"${ideal_lower:.2f} - ${ideal_upper:.2f}",
        "stop_loss": stop_loss,
        "pros": pros,
        "cons": cons
    }

# ================= 6. 前端主控交互 =================
st.markdown("### 🧭 ReasonVest 全美股全维决策终端")

# 宏观水温与刷新
vix_val, tnx_val = fetch_global_macro()
col_m1, col_m2 = st.columns([2, 1])
with col_m1:
    st.caption(f"🌍 **宏观水温**：VIX 恐慌指数 `{vix_val}` | 美债 10年期 `{tnx_val}%`")
with col_m2:
    if st.button("🔄 刷新全网数据", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# 顶层两大核心模式导航
main_mode = st.radio(
    "功能模式切换：",
    ["🏛️ 主界面：20大核心股与分类资产", "🔤 字母检索全景大厅 (8000+标的与资讯)"],
    horizontal=True
)

chosen_ticker = "NVDA"

# ----------------- 模式 1: 主界面分类展台 -----------------
if main_mode == "🏛️ 主界面：20大核心股与分类资产":
    selected_pool_name = st.selectbox(
        "切换资产池分类：",
        options=list(CURATED_POOLS.keys()),
        index=0
    )

    with st.spinner(f"加载【{selected_pool_name}】实时财务与行情..."):
        df_pool = fetch_pool_metrics(selected_pool_name)

    st.dataframe(
        df_pool[["Ticker", "公司名称", "核心业务", "现价($)", "营收增速", "毛利率", "前瞻PE", "市值(B)"]],
        use_container_width=True,
        hide_index=True
    )

    chosen_ticker = st.selectbox(
        f"从上方【{selected_pool_name}】选定一只展开全维量化体检:",
        options=df_pool["Ticker"].tolist() if not df_pool.empty else ["NVDA"]
    )

# ----------------- 模式 2: 字母检索与全景资讯大厅 -----------------
else:
    with st.spinner("同步 SEC 全美股官方 8000+ 标的名录..."):
        all_sec_stocks = load_all_sec_us_stocks()

    col_l1, col_l2 = st.columns([1, 2])
    with col_l1:
        search_letter = st.text_input("输入检索字母 (如 N, A, T...):", value="N").upper().strip()
        if not search_letter:
            search_letter = "N"

    matched_stocks = [s for s in all_sec_stocks if s["ticker"].startswith(search_letter)]
    total_matches = len(matched_stocks)

    with col_l2:
        st.caption(f"📊 检索结果：全美股以 **【{search_letter}】** 开头的上市公司共 **{total_matches}** 只")

    if total_matches == 0:
        st.warning(f"未找到以 {search_letter} 开头的股票。")
        st.stop()

    PAGE_SIZE = 15
    total_pages = max(1, (total_matches + PAGE_SIZE - 1) // PAGE_SIZE)
    current_page = st.selectbox(
        f"翻页浏览 (每页 {PAGE_SIZE} 只):",
        options=[f"第 {p+1} 页 ({p*PAGE_SIZE+1} - {min((p+1)*PAGE_SIZE, total_matches)})" for p in range(total_pages)],
        index=0
    )
    page_idx = int(current_page.split()[1]) - 1
    page_items = matched_stocks[page_idx * PAGE_SIZE : (page_idx + 1) * PAGE_SIZE]
    page_tickers = [item["ticker"] for item in page_items]

    with st.spinner(f"拉取第 {page_idx+1} 页股票实时报价..."):
        df_page_quotes = fetch_batch_page_quotes(page_tickers)

    df_page_display = pd.DataFrame(page_items)[["ticker", "name"]].rename(columns={"ticker": "Ticker", "name": "公司全称"})
    df_merged = pd.merge(df_page_display, df_page_quotes, on="Ticker", how="left")

    st.markdown(f"##### 📋 【{search_letter}】开头股票列表与实时报价")
    st.dataframe(
        df_merged[["Ticker", "公司全称", "现价($)", "涨跌幅"]],
        use_container_width=True,
        hide_index=True
    )

    chosen_ticker = st.selectbox(
        f"在【{search_letter}】列表中选中目标股票 (直接调取其专属资讯与量化体检):",
        options=page_tickers,
        index=0
    )

st.markdown("---")

# ================= 7. 选中标的的深度全维资讯与综合评价 =================
try:
    with st.spinner(f"正在全维调取 {chosen_ticker} 的最新行情、一手外媒与财务健康度..."):
        info, hist, insider_status, beat_rate, stock_news = fetch_single_stock_all(chosen_ticker)
        c_price = info.get("currentPrice") or info.get("regularMarketPrice", 0.0)
        p_close = info.get("previousClose", c_price)
        pct = ((c_price - p_close) / p_close * 100) if p_close else 0.0
except Exception as e:
    st.error(f"标的数据拉取异常: {e}")
    st.stop()

# 标的实时核心卡片
st.markdown(f"""
<div class="mobile-card">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <h2 style="margin:0; padding:0;">{info.get('shortName', chosen_ticker)} ({chosen_ticker})</h2>
            <span style="color:#8b949e; font-size:13px;">{info.get('sector', '美股标的')} · {info.get('industry', '')}</span>
        </div>
        <div style="text-align:right;">
            <h2 style="margin:0; padding:0;">${c_price:.2f}</h2>
            <span style="color:{'#26a69a' if pct>=0 else '#ef5350'}; font-weight:bold;">{pct:+.2f}%</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 标签页控制
tab_eval, tab_news, tab_chart = st.tabs([
    "🧠 全维量化综合评价", 
    f"📰 {chosen_ticker} 专属实时外媒资讯", 
    "📈 实时K线走势"
])

# ================= TAB 1: 全维量化综合评价 =================
with tab_eval:
    eval_res = run_master_evaluation(info, hist, c_price, vix_val, tnx_val, insider_status, beat_rate)
    v_color = "🟢" if "推荐" in eval_res['verdict'] or "买入" in eval_res['verdict'] else ("🔴" if "规避" in eval_res['verdict'] else "🟡")

    st.markdown(f"""
    <div class="mobile-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span>量化综合打分: <b style="font-size:18px; color:#58a6ff;">{eval_res['score']} / 100</b></span>
            <span>评级: <b>{v_color} {eval_res['verdict']}</b></span>
        </div>
        <div style="margin-top:6px;">
            <span>短期走势推演 (1-3月): <b>{eval_res['short_bias']}</b></span>
        </div>
        <p style="margin:8px 0 0 0; font-size:13px; color:#c9d1d9; line-height:1.5;">{eval_res['horizon_desc']}</p>
    </div>
    """, unsafe_allow_html=True)

    g1, g2 = st.columns(2)
    with g1:
        st.markdown(f"""
        <div class="grid-pill">
            <span style="font-size:12px; color:#8b949e;">📊 历史估值分位 (PE Percentile)</span><br>
            <b>{eval_res['pe_percentile']}%</b> ({'偏低低估' if eval_res['pe_percentile']<35 else ('偏高过热' if eval_res['pe_percentile']>80 else '合理中枢')})
        </div>
        <div class="grid-pill">
            <span style="font-size:12px; color:#8b949e;">🏆 历史财报超预期率</span><br>
            <b>{beat_rate}</b>
        </div>
        <div class="grid-pill">
            <span style="font-size:12px; color:#8b949e;">🎯 最佳建仓挂单区间</span><br>
            <b style="color:#58a6ff;">{eval_res['buy_zone']}</b>
        </div>
        """, unsafe_allow_html=True)
    with g2:
        st.markdown(f"""
        <div class="grid-pill">
            <span style="font-size:12px; color:#8b949e;">👔 SEC Form 4 高管增减持</span><br>
            <b>{insider_status}</b>
        </div>
        <div class="grid-pill">
            <span style="font-size:12px; color:#8b949e;">📈 技术面 RSI(14) 状态</span><br>
            <b>{eval_res['rsi_val']}</b> ({'超卖区' if eval_res['rsi_val']<38 else ('超买区' if eval_res['rsi_val']>70 else '中性区')})
        </div>
        <div class="grid-pill" style="border-left-color: #ef5350;">
            <span style="font-size:12px; color:#8b949e;">🚨 破位严格止损红线</span><br>
            <b style="color:#ef5350;">${eval_res['stop_loss']}</b>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.success("### ✅ 为什么推荐它 (多头核心动能)")
    for p in eval_res['pros']:
        st.markdown(p)

    st.error("### ❌ 为什么不推荐它 (核心空头风险)")
    for c in eval_res['cons']:
        st.markdown(c)

# ================= TAB 2: 该标的专属突发一手资讯 =================
with tab_news:
    st.markdown(f"#### ⚡ 【{chosen_ticker}】实时外媒突发资讯 (Reuters / CNBC / Bloomberg)")
    if stock_news:
        for item in stock_news[:10]:
            title = item.get("title") or item.get("content", {}).get("title", "最新快讯")
            publisher = item.get("publisher") or item.get("content", {}).get("provider", {}).get("displayName", "权威外媒")
            link = item.get("link") or item.get("content", {}).get("canonicalUrl", {}).get("url", "#")
            pub_time = item.get("providerPublishTime")
            time_str = datetime.fromtimestamp(pub_time).strftime('%m-%d %H:%M') if pub_time else "突发"

            st.markdown(f"""
            <div style="border-bottom:1px solid #21262d; padding:10px 0;">
                <span class="news-badge">{publisher} · {time_str}</span><br>
                <a href="{link}" target="_blank" style="color:#58a6ff; text-decoration:none; font-size:13px; font-weight:500;">{title}</a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info(f"近期暂无关于 {chosen_ticker} 的重大突发新闻。")

# ================= TAB 3: 实时 K 线走势 =================
with tab_chart:
    st.caption("近 1 年 K 线与历史阻力支撑位")
    if not hist.empty and len(hist) > 1:
        dates = pd.to_datetime(hist.index).strftime('%Y-%m-%d')
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=dates, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name="K线"
        ))
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=340,
            margin=dict(l=5, r=5, t=10, b=10),
            template="plotly_dark",
            paper_bgcolor="#181b26", plot_bgcolor="#181b26"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("暂未获取到近期交易日 K 线。")
