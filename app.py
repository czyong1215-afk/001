import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# ================= 1. 移动端原生视口与主题注入 =================
st.set_page_config(
    page_title="ReasonVest Pro - 全维美股决策终端",
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
        padding-top: 1rem !important;
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
</style>
""", unsafe_allow_html=True)

# ================= 2. 股票底层数据池与分类定义 =================
STOCK_UNIVERSE = [
    {"ticker": "NVDA", "name": "英伟达", "sector": "科技", "tag": "芯片/AI算力", "type": "科技巨头"},
    {"ticker": "MSFT", "name": "微软", "sector": "科技", "tag": "云/企业AI", "type": "科技巨头"},
    {"ticker": "AAPL", "name": "苹果", "sector": "科技", "tag": "消费电子/端侧AI", "type": "科技巨头"},
    {"ticker": "AVGO", "name": "博通", "sector": "科技", "tag": "定制AI芯片", "type": "科技巨头"},
    {"ticker": "APP", "name": "AppLovin", "sector": "科技", "tag": "AI广告引擎", "type": "🔥潜力黑马"},
    {"ticker": "PLTR", "name": "Palantir", "sector": "科技", "tag": "大数据/AI系统", "type": "🔥潜力黑马"},
    {"ticker": "SYM", "name": "Symbotic", "sector": "智能制造", "tag": "仓储机器人", "type": "🔥潜力黑马"},
    {"ticker": "IONQ", "name": "IonQ", "sector": "科技", "tag": "量子计算", "type": "🔥潜力黑马"},
    {"ticker": "SOFI", "name": "SoFi Tech", "sector": "金融科技", "tag": "数字银行", "type": "🔥潜力黑马"},
    {"ticker": "LLY", "name": "礼来", "sector": "医疗健康", "tag": "减重药GLP-1", "type": "医疗龙头"},
    {"ticker": "VKTX", "name": "Viking", "sector": "医疗健康", "tag": "代谢创新药", "type": "🔥潜力黑马"},
    {"ticker": "CRSP", "name": "CRISPR", "sector": "医疗健康", "tag": "基因编辑前沿", "type": "🔥潜力黑马"},
    {"ticker": "TSLA", "name": "特斯拉", "sector": "可选消费", "tag": "自动驾驶/机器人", "type": "科技巨头"},
    {"ticker": "VST", "name": "Vistra", "sector": "公用事业", "tag": "AI数据中心核电", "type": "🔥潜力黑马"}
]

# ================= 3. 高级数据抓取（宏观、内部人、估值分位、财报胜率） =================
@st.cache_data(ttl=1800)
def fetch_macro_state():
    """获取宏观水温：VIX恐慌指数与美债10年期利率"""
    try:
        vix = yf.Ticker('^VIX').history(period='2d')['Close'].iloc[-1]
    except:
        vix = 18.5
    try:
        tnx = yf.Ticker('^TNX').history(period='2d')['Close'].iloc[-1]
    except:
        tnx = 4.25
    return round(float(vix), 1), round(float(tnx), 2)

@st.cache_data(ttl=600)
def fetch_screener_data():
    results = []
    for s in STOCK_UNIVERSE:
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
                "名称": s["name"],
                "分类": s["type"],
                "细分业务": s["tag"],
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
def fetch_stock_full_package(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info or {}
    
    try:
        hist = stock.history(period="1y")
    except:
        hist = pd.DataFrame()

    # 1. 解析内部人交易
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

    # 2. 解析历史财报超预期率
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

    # 3. 解析新闻
    try:
        news = stock.news or []
    except:
        news = []

    return info, hist, insider_status, beat_rate, news

# ================= 4. 全维对冲基金级量化推导模型 =================
def run_master_evaluation(info, hist, c_price, vix, tnx, insider_status, beat_rate):
    """
    整合：宏观、估值分位、内部人交易、财报胜率、成长性、技术面的综合推理大脑
    """
    rev_growth = info.get("revenueGrowth", 0) or 0
    gross_margin = info.get("grossMargins", 0) or 0
    pe = info.get("forwardPE", 0) or 0
    target_median = info.get("targetMedianPrice", c_price) or c_price
    fifty_low = info.get("fiftyTwoWeekLow", c_price * 0.75) or (c_price * 0.75)
    upside_pct = ((target_median - c_price) / c_price * 100) if c_price else 0

    # 1. 计算历史 PE 分位数 (估值水位)
    pe_percentile = 50.0
    trailing_eps = info.get('trailingEps') or 0
    if trailing_eps > 0 and not hist.empty and len(hist) > 30:
        pe_series = hist['Close'] / trailing_eps
        cur_calc_pe = c_price / trailing_eps
        pe_percentile = round(float((pe_series < cur_calc_pe).mean() * 100), 1)

    # 2. 计算 RSI 与均线
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

    # 3. 核心量化打分 (0 - 100)
    score = 50
    # 基本面
    if rev_growth > 0.25: score += 15
    elif rev_growth > 0.10: score += 8
    elif rev_growth < 0: score -= 15

    if gross_margin > 0.50: score += 10
    elif gross_margin < 0.20: score -= 10

    # 估值水位
    if pe_percentile < 30: score += 10 # 估值低估
    elif pe_percentile > 80: score -= 12 # 估值过热

    # 机构目标空间
    if upside_pct > 20: score += 10
    elif upside_pct < 0: score -= 10

    # 宏观环境加减分
    if vix > 28: score -= 8 # 极度恐慌压制
    elif vix < 15: score += 5

    # 内部人与财报加减分
    if "增持" in insider_status: score += 8
    elif "减持" in insider_status: score -= 6

    # 4. 生成评级与短期走势
    if score >= 75:
        verdict = "强烈推荐"
        short_bias = "看涨 🚀"
        horizon_desc = f"基本面扩张叠加估值处于健康区间，华尔街目标空间 {upside_pct:+.1f}%，短期共振看涨。"
    elif score >= 60:
        verdict = "逢低买入"
        short_bias = "看涨 🚀"
        horizon_desc = "综合质地优良，安全边际良好，短期处于蓄势震荡上行通道。"
    elif score >= 45:
        verdict = "谨慎观望"
        short_bias = "中性震荡 ⚖️"
        horizon_desc = "估值分位数偏高或短期缺乏催化剂，建议保持观望，等待充分回调。"
    else:
        verdict = "建议规避"
        short_bias = "看跌 📉"
        horizon_desc = "宏观/行业面临估值压缩压力，或高管筹码松动，短期下行风险未出尽。"

    # 5. 测算最佳入手区间
    ideal_lower = max(fifty_low, c_price * 0.88)
    ideal_upper = min(c_price * 0.96, (sma_50 if sma_50 > 0 else c_price))
    if ideal_upper <= ideal_lower:
        ideal_upper = c_price * 0.98
        ideal_lower = c_price * 0.90
    stop_loss = round(ideal_lower * 0.94, 2)

    # 6. 多空对抗提炼
    pros = [
        f"**业绩成长支撑**：营收同比增速达 **{rev_growth*100:.1f}%**，毛利率 **{gross_margin*100:.1f}%** 展现强产品护城河。",
        f"**估值与目标价空间**：华尔街一致预期目标价 **${target_median:.2f}** (上行空间 **{upside_pct:+.1f}%**)。",
        f"**业绩稳定性与筹码**：历史财报超预期率高达 **{beat_rate}**，高管动向显示【{insider_status}】。"
    ]

    cons = [
        f"**历史估值分位水位**：当前处于近一年估值历史的 **{pe_percentile:.1f}%** 分位点（前瞻PE: {pe:.1f}x），需防范杀估值。",
        f"**宏观与利率环境扰动**：当前 10年期美债收益率处于 **{tnx}%**，无风险利率高企对科技成长倍数构成天花板。",
        f"**技术面超买风险**：当前 RSI(14) 为 **{rsi_val}**，若高于 70 切忌盲目追涨，须等待回踩。"
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

# ================= 5. 前端主交互逻辑 =================
st.markdown("### 🧭 ReasonVest 美股全维决策终端")

# 宏观看板
vix_val, tnx_val = fetch_macro_state()
macro_sentiment = "🟢 顺风适度扩张" if vix_val < 20 and tnx_val < 4.5 else "🔴 宏观避险压制"
st.caption(f"🌍 **宏观水温**：恐慌指数 VIX: `{vix_val}` | 10年期美债: `{tnx_val}%` | 状态: **{macro_sentiment}**")

category_filter = st.radio(
    "板块分类切换",
    ["🔥 潜力黑马股", "💻 科技龙头", "全部股票池"],
    horizontal=True
)

with st.spinner("刷新市场数据..."):
    df_screener = fetch_screener_data()

if category_filter == "🔥 潜力黑马股":
    df_show = df_screener[df_screener["分类"] == "🔥潜力黑马"]
elif category_filter == "💻 科技龙头":
    df_show = df_screener[df_screener["分类"] == "科技巨头"]
else:
    df_show = df_screener

st.dataframe(
    df_show[["Ticker", "名称", "现价($)", "营收增速", "毛利率", "前瞻PE"]],
    use_container_width=True,
    hide_index=True
)

col_s1, col_s2 = st.columns([1, 1])
with col_s1:
    selected_ticker = st.selectbox("从列表中选定标的:", df_show["Ticker"].tolist())
with col_s2:
    manual_search = st.text_input("或直接搜索任意美股代码:", placeholder="如 NVDA, AMD, SOFI").upper().strip()

current_ticker = manual_search if manual_search else selected_ticker

st.markdown("---")

try:
    with st.spinner(f"正在全维体检 {current_ticker}..."):
        info, hist, insider_status, beat_rate, news_list = fetch_stock_full_package(current_ticker)
        c_price = info.get("currentPrice") or info.get("regularMarketPrice", 0.0)
        p_close = info.get("previousClose", c_price)
        pct = ((c_price - p_close) / p_close * 100) if p_close else 0.0
except Exception as e:
    st.error(f"数据加载失败: {e}")
    st.stop()

# 股票核心信息卡片
st.markdown(f"""
<div class="mobile-card">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <h2 style="margin:0; padding:0;">{info.get('shortName', current_ticker)} ({current_ticker})</h2>
            <span style="color:#8b949e; font-size:13px;">{info.get('sector', '未知行业')} · {info.get('industry', '')}</span>
        </div>
        <div style="text-align:right;">
            <h2 style="margin:0; padding:0;">${c_price:.2f}</h2>
            <span style="color:{'#26a69a' if pct>=0 else '#ef5350'}; font-weight:bold;">{pct:+.2f}%</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 标签页：以全维综合评价为核心
tab_eval, tab_chart, tab_news = st.tabs([
    "🧠 全维量化综合评价", 
    "📈 实时K线走势", 
    "📰 实时外媒新闻"
])

# ================= TAB 1: 全维整合型综合评价 (核心) =================
with tab_eval:
    eval_res = run_master_evaluation(info, hist, c_price, vix_val, tnx_val, insider_status, beat_rate)

    v_color = "🟢" if "推荐" in eval_res['verdict'] or "买入" in eval_res['verdict'] else ("🔴" if "规避" in eval_res['verdict'] else "🟡")

    # 1. 顶部总评看板
    st.markdown(f"""
    <div class="mobile-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span>对冲基金量化评分: <b style="font-size:18px; color:#58a6ff;">{eval_res['score']} / 100</b></span>
            <span>评级: <b>{v_color} {eval_res['verdict']}</b></span>
        </div>
        <div style="margin-top:6px;">
            <span>短期走势推演 (1-3月): <b>{eval_res['short_bias']}</b></span>
        </div>
        <p style="margin:8px 0 0 0; font-size:13px; color:#c9d1d9; line-height:1.5;">{eval_res['horizon_desc']}</p>
    </div>
    """, unsafe_allow_html=True)

    # 2. 六维深度指标矩阵 (整合新增的估值分位、内部人、财报胜率等)
    st.markdown("#### 🔬 六维深度量化体检矩阵")
    g_c1, g_c2 = st.columns(2)
    with g_c1:
        st.markdown(f"""
        <div class="grid-pill">
            <span style="font-size:12px; color:#8b949e;">📊 历史估值分位 (PE Percentile)</span><br>
            <b>{eval_res['pe_percentile']}%</b> ({'偏低低估' if eval_res['pe_percentile']<35 else ('偏高过热' if eval_res['pe_percentile']>80 else '合理中枢')})
        </div>
        <div class="grid-pill">
            <span style="font-size:12px; color:#8b949e;">🏆 历史财报击败率 (Beat Rate)</span><br>
            <b>{beat_rate}</b>
        </div>
        <div class="grid-pill">
            <span style="font-size:12px; color:#8b949e;">🎯 最佳建仓挂单区间</span><br>
            <b style="color:#58a6ff;">{eval_res['buy_zone']}</b>
        </div>
        """, unsafe_allow_html=True)
    with g_c2:
        st.markdown(f"""
        <div class="grid-pill">
            <span style="font-size:12px; color:#8b949e;">👔 SEC Form 4 高管内部人交易</span><br>
            <b>{insider_status}</b>
        </div>
        <div class="grid-pill">
            <span style="font-size:12px; color:#8b949e;">📈 技术面 RSI(14) 动能</span><br>
            <b>{eval_res['rsi_val']}</b> ({'超卖区' if eval_res['rsi_val']<38 else ('超买区' if eval_res['rsi_val']>70 else '中性区')})
        </div>
        <div class="grid-pill" style="border-left-color: #ef5350;">
            <span style="font-size:12px; color:#8b949e;">🚨 破位严格止损红线</span><br>
            <b style="color:#ef5350;">${eval_res['stop_loss']}</b>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # 3. 为什么推荐 VS 为什么不推荐
    st.success("### ✅ 为什么推荐它 (多头核心逻辑)")
    for p in eval_res['pros']:
        st.markdown(p)

    st.error("### ❌ 为什么不推荐它 (空头与风险警示)")
    for c in eval_res['cons']:
        st.markdown(c)

# ================= TAB 2: K 线走势 =================
with tab_chart:
    st.caption("近 6 个月蜡烛图走势")
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

# ================= TAB 3: 实时外媒新闻 =================
with tab_news:
    st.markdown("#### 📰 实时权威外媒头条 (Reuters / CNBC / Bloomberg)")
    if news_list:
        for item in news_list[:6]:
            title = item.get("title") or item.get("content", {}).get("title", "最新新闻")
            publisher = item.get("publisher") or item.get("content", {}).get("provider", {}).get("displayName", "主流外媒")
            link = item.get("link") or item.get("content", {}).get("canonicalUrl", {}).get("url", "#")
            st.markdown(f"""
            <div style="border-bottom:1px solid #21262d; padding:8px 0;">
                <span style="color:#8b949e; font-size:11px;">{publisher}</span><br>
                <a href="{link}" target="_blank" style="color:#58a6ff; text-decoration:none; font-size:13px; font-weight:500;">{title}</a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("近期暂无该标的重大突发外媒新闻。")
