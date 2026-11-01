import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# ================= 1. 移动端原生视口与主题注入 =================
st.set_page_config(
    page_title="ReasonVest Pro - 美股量化与入场时机终端",
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

@st.cache_data(ttl=180)
def fetch_stock_full_package(ticker):
    """安全拉取股票的所有数据：行情、K线、财报、新闻、财报日历"""
    stock = yf.Ticker(ticker)
    info = stock.info or {}
    
    try:
        hist = stock.history(period="6mo")
    except:
        hist = pd.DataFrame()
        
    try:
        fin = stock.financials
        if fin is None: fin = pd.DataFrame()
    except:
        fin = pd.DataFrame()

    # 抓取外媒新闻 (Reuters, CNBC, Bloomberg 等合作源)
    try:
        news = stock.news or []
    except:
        news = []

    # 抓取下一次财报会议日期
    try:
        calendar = stock.calendar
    except:
        calendar = {}

    return info, hist, fin, news, calendar

# ================= 3. 最佳入手时机测算模型 (Entry Timing Model) =================
def compute_best_entry_timing(info, hist, c_price):
    """
    推导何时入手最值得：
    结合：RSI(14)、200日均线、华尔街目标价折扣、52周支撑位
    """
    fifty_low = info.get("fiftyTwoWeekLow", c_price * 0.75) or (c_price * 0.75)
    target_median = info.get("targetMedianPrice", c_price) or c_price
    upside_pct = ((target_median - c_price) / c_price * 100) if c_price else 0

    # 1. 计算 RSI (相对强弱指标)
    rsi_val = 50.0
    sma_50 = c_price
    sma_200 = c_price
    if not hist.empty and len(hist) >= 15:
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        rsi_series = 100 - (100 / (1 + rs))
        rsi_val = rsi_series.iloc[-1] if not pd.isna(rsi_series.iloc[-1]) else 50.0

        if len(hist) >= 50:
            sma_50 = hist['Close'].rolling(50).mean().iloc[-1]
        if len(hist) >= 120:
            sma_200 = hist['Close'].rolling(120).mean().iloc[-1]

    # 2. 测算最佳入手区间 (Buy Zone)
    # 策略：以近期的技术支撑位与合理安全边际计算
    ideal_lower_entry = max(fifty_low, c_price * 0.88)
    ideal_upper_entry = min(c_price * 0.96, (sma_50 if sma_50 > 0 else c_price))
    if ideal_upper_entry <= ideal_lower_entry:
        ideal_upper_entry = c_price * 0.98
        ideal_lower_entry = c_price * 0.90

    # 3. 研判当前入场时机评级
    # 条件A: RSI < 38 严重超跌
    # 条件B: 离目标价有 > 25% 空间
    # 条件C: 价格接近支撑位
    if rsi_val < 38 and upside_pct > 20:
        timing_status = "🔥 极佳买点（黄金超跌买入区）"
        action_advice = f"技术面 RSI 出现严重超卖信号 ({rsi_val:.1f})，且华尔街目标价有 {upside_pct:+.1f}% 空间，此时入手盈亏比极高，建议立即分批建仓。"
    elif c_price <= ideal_upper_entry:
        timing_status = "✅ 适合分批吸筹（处于安全边际内）"
        action_advice = f"当前价格已进入量化模型测算的建仓区间 (${ideal_lower_entry:.2f} ~ ${ideal_upper_entry:.2f})，可采取【三批建仓法】逢低配置。"
    elif rsi_val > 70:
        timing_status = "⚠️ 严重超买（切勿追高追涨）"
        action_advice = f"短期 RSI 指标高达 {rsi_val:.1f}，动能严重超买透支，追高极易被套！**最值得入手的时机是耐心等待价格回踩至 ${ideal_upper_entry:.2f} 附近再考虑入场**。"
    else:
        timing_status = "⏳ 观望等待（等待更低挂单点）"
        action_advice = f"当前处于震荡观望区间，建议保持耐心，把限价买单挂在 **${ideal_lower_entry:.2f} - ${ideal_upper_entry:.2f}** 区间静待回踩。"

    return {
        "timing_status": timing_status,
        "action_advice": action_advice,
        "buy_zone_low": round(ideal_lower_entry, 2),
        "buy_zone_high": round(ideal_upper_entry, 2),
        "rsi": round(rsi_val, 1),
        "upside_pct": round(upside_pct, 1),
        "sma_50": round(sma_50, 2)
    }

# ================= 4. 主界面渲染 =================
st.markdown("### 🧭 ReasonVest 美股全维决策终端")

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
    with st.spinner(f"正在全维追踪 {current_ticker} 的行情、新闻、财报会议..."):
        info, hist, fin, news_list, calendar = fetch_stock_full_package(current_ticker)
        c_price = info.get("currentPrice") or info.get("regularMarketPrice", 0.0)
        p_close = info.get("previousClose", c_price)
        pct = ((c_price - p_close) / p_close * 100) if p_close else 0.0
except Exception as e:
    st.error(f"数据拉取失败，请检查 Ticker: {e}")
    st.stop()

# 顶部核心信息卡片
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

# 四大核心模块标签页
tab_entry, tab_news, tab_reason, tab_chart = st.tabs([
    "🎯 最佳入手时机", 
    "📰 实时外媒新闻与会议", 
    "🧠 多空综合评价", 
    "📈 实时K线走势"
])

# ------------ TAB 1: 核心需求 - 最佳入手时机测算 ------------
with tab_entry:
    st.markdown("#### 🎯 量化测算：什么时候入手最值得？")
    timing = compute_best_entry_timing(info, hist, c_price)

    st.markdown(f"""
    <div class="mobile-card">
        <h4 style="margin:0 0 8px 0; color:#e6edf3;">当前买入时机评级：</h4>
        <h3 style="margin:0 0 12px 0;">{timing['timing_status']}</h3>
        <p style="font-size:14px; color:#c9d1d9; line-height:1.6;">{timing['action_advice']}</p>
    </div>
    """, unsafe_allow_html=True)

    c_b1, c_b2 = st.columns(2)
    with c_b1:
        st.metric("🎯 最佳建仓挂单区间", f"${timing['buy_zone_low']} - ${timing['buy_zone_high']}")
    with c_b2:
        st.metric("RSI(14) 超买超卖指标", f"{timing['rsi']}", "超卖 (<35) / 超买 (>70)")

    st.info(f"""
    💡 **最稳妥的入手操作法则**：
    1. **拒绝追高**：如果当前价格高于 **${timing['buy_zone_high']}**，不要市价急于追入；
    2. **埋伏挂单**：将首笔买入资金（如 30%）挂在 **${timing['buy_zone_high']}**，次笔资金挂在 **${timing['buy_zone_low']}**；
    3. **破位保护**：一旦放量跌破 **${timing['buy_zone_low'] * 0.95:.2f}**，立即停止补仓，防范假摔变成破位下行。
    """)

# ------------ TAB 2: 核心需求 - 实时外媒新闻与财报会议追踪 ------------
with tab_news:
    st.markdown("#### 📅 财报会议与事件日历")
    # 解析财报日期
    earnings_date_str = "暂无公布"
    if isinstance(calendar, dict) and "Earnings Date" in calendar:
        e_dates = calendar["Earnings Date"]
        if e_dates:
            earnings_date_str = str(e_dates[0])
    
    st.markdown(f"""
    <div class="mobile-card">
        <span style="color:#8b949e; font-size:13px;">下一次财报发布与业绩电话会议 (Earnings Call)</span>
        <h3 style="margin:6px 0 0 0; color:#58a6ff;">📆 {earnings_date_str}</h3>
        <p style="font-size:12px; color:#8b949e; margin-top:4px;">*注：若距离财报会不足 7 个交易日，请严格控制仓位，避免盲盒暴击风险。</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 📰 实时外媒财经新闻头条 (Reuters / CNBC / Bloomberg)")
    if news_list:
        for item in news_list[:8]: # 展示最新8条新闻
            # 兼容不同 yfinance 版本的 news 字典结构
            title = item.get("title") or item.get("content", {}).get("title", "新闻标题")
            publisher = item.get("publisher") or item.get("content", {}).get("provider", {}).get("displayName", "权威外媒")
            link = item.get("link") or item.get("content", {}).get("canonicalUrl", {}).get("url", "#")
            pub_time = item.get("providerPublishTime")
            time_str = datetime.fromtimestamp(pub_time).strftime('%m-%d %H:%M') if pub_time else "最新"

            st.markdown(f"""
            <div style="border-bottom:1px solid #21262d; padding:10px 0;">
                <span style="background:#21262d; color:#8b949e; font-size:11px; padding:2px 6px; border-radius:4px;">{publisher} · {time_str}</span>
                <div style="margin-top:6px;">
                    <a href="{link}" target="_blank" style="color:#58a6ff; text-decoration:none; font-size:14px; font-weight:500;">{title}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("近期暂无该标的重大突发外媒新闻更新。")

# ------------ TAB 3: 多空综合定量评价 ------------
with tab_reason:
    st.markdown("#### 🧠 核心财务与量化多空对抗")
    rev_growth = info.get("revenueGrowth", 0) or 0
    gross_margin = info.get("grossMargins", 0) or 0
    pe = info.get("forwardPE", 0) or 0
    target_median = info.get("targetMedianPrice", c_price) or c_price
    upside_pct = ((target_median - c_price) / c_price * 100) if c_price else 0

    st.success("### ✅ 为什么推荐它 (做多逻辑)")
    st.markdown(f"1. **业绩增长支撑**：最新季度营收同比增速达 **{rev_growth*100:.1f}%**，基本面维持扩张。")
    st.markdown(f"2. **毛利护城河**：毛利率达 **{gross_margin*100:.1f}%**，在细分领域具备产品自主定价权。")
    st.markdown(f"3. **机构目标空间**：华尔街一致预期目标价为 **${target_median:.2f}** (潜在空间: {upside_pct:+.1f}%)。")

    st.error("### ❌ 为什么不推荐它 (核心风险)")
    st.markdown(f"1. **估值溢价压力**：前瞻 PE 为 **{pe:.1f}x**，业绩稍有不及预期容易产生估值下杀。")
    st.markdown(f"2. **宏观联动风险**：美联储宏观流动性预期波动可能对科技/高成长股估值带来系统性压制。")
    st.markdown(f"3. **黑天鹅与竞争**：密切追踪外媒新闻中关于竞品替代、监管反垄断或主要客户砍单的异动。")

# ------------ TAB 4: K 线走势 ------------
with tab_chart:
    st.caption("近 6 个月 K 线与均线支撑")
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
