import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

# ================= 1. 移动端原生视口与主题注入 =================
st.set_page_config(
    page_title="ReasonVest - 美股量化推理终端",
    page_icon="📈",
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
    # 科技龙头
    {"ticker": "NVDA", "name": "英伟达", "sector": "科技", "tag": "芯片/AI算力", "type": "科技巨头"},
    {"ticker": "MSFT", "name": "微软", "sector": "科技", "tag": "云/企业AI", "type": "科技巨头"},
    {"ticker": "AAPL", "name": "苹果", "sector": "科技", "tag": "消费电子/端侧AI", "type": "科技巨头"},
    {"ticker": "AVGO", "name": "博通", "sector": "科技", "tag": "定制AI芯片", "type": "科技巨头"},
    # 潜力黑马股
    {"ticker": "APP", "name": "AppLovin", "sector": "科技", "tag": "AI广告引擎", "type": "🔥潜力黑马"},
    {"ticker": "PLTR", "name": "Palantir", "sector": "科技", "tag": "大数据/AI系统", "type": "🔥潜力黑马"},
    {"ticker": "SYM", "name": "Symbotic", "sector": "智能制造", "tag": "仓储机器人", "type": "🔥潜力黑马"},
    {"ticker": "IONQ", "name": "IonQ", "sector": "科技", "tag": "量子计算", "type": "🔥潜力黑马"},
    {"ticker": "SOFI", "name": "SoFi Tech", "sector": "金融科技", "tag": "数字银行", "type": "🔥潜力黑马"},
    # 医疗与生物创新药
    {"ticker": "LLY", "name": "礼来", "sector": "医疗健康", "tag": "减重药GLP-1", "type": "医疗龙头"},
    {"ticker": "VKTX", "name": "Viking", "sector": "医疗健康", "tag": "代谢创新药", "type": "🔥潜力黑马"},
    {"ticker": "CRSP", "name": "CRISPR", "sector": "医疗健康", "tag": "基因编辑前沿", "type": "🔥潜力黑马"},
    # 能源变革与工业制造
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

@st.cache_data(ttl=300)
def fetch_stock_details(ticker):
    stock = yf.Ticker(ticker)
    return stock.info, stock.history(period="3mo"), stock.financials

# ================= 3. 核心量化推理算法 (免 API Key 核心) =================
def run_quant_reasoning(info, c_price):
    """纯本地算法：基于真实财报和市场指标推导多空逻辑"""
    rev_growth = info.get("revenueGrowth", 0) or 0
    gross_margin = info.get("grossMargins", 0) or 0
    pe = info.get("forwardPE", 0) or 0
    target_median = info.get("targetMedianPrice", c_price) or c_price
    short_ratio = info.get("shortRatio", 0) or 0
    fifty_low = info.get("fiftyTwoWeekLow", c_price * 0.7) or (c_price * 0.7)

    upside_pct = ((target_median - c_price) / c_price * 100) if c_price else 0

    # 1. 评级推导打分机制
    score = 50
    if rev_growth > 0.25: score += 20
    elif rev_growth > 0.10: score += 10
    elif rev_growth < 0: score -= 20

    if gross_margin > 0.50: score += 15
    elif gross_margin < 0.20: score -= 15

    if upside_pct > 20: score += 15
    elif upside_pct < 0: score -= 15

    if pe and pe > 60: score -= 10

    # 2. 生成评级与短期方向
    if score >= 75:
        verdict = "强烈推荐"
        short_bias = "看涨"
        horizon = f"华尔街一致预期目标价空间达 {upside_pct:+.1f}%，高营收增速有望在下个财报季催化估值重估。"
    elif score >= 60:
        verdict = "逢低买入"
        short_bias = "看涨"
        horizon = f"基本面健康，目前价格具备合理安全边际，短期以震荡上行为主。"
    elif score >= 45:
        verdict = "谨慎观望"
        short_bias = "震荡"
        horizon = "估值已充分计入当前增长预期，短期缺乏强催化剂，建议等待回调或新业绩确认。"
    else:
        verdict = "建议规避"
        short_bias = "看跌"
        horizon = "基本面增速承压或估值明显透支，短期存在下行修正压力。"

    # 3. 提取 3 条核心推荐理由
    pros = []
    if rev_growth > 0.15:
        pros.append(f"**业绩爆发力强**：最新季度营收同比增速达 {rev_growth*100:.1f}%，处于行业前列。")
    else:
        pros.append(f"**经营韧性稳健**：业务现金流健康，抵御宏观周期波动能力较强。")

    if gross_margin > 0.40:
        pros.append(f"**产品护城河深厚**：毛利率高达 {gross_margin*100:.1f}%，具备极强的产品定价权与议价能力。")
    else:
        pros.append(f"**市场渗透潜力**：处于行业放量周期，规模效应逐步释放。")

    if upside_pct > 0:
        pros.append(f"**机构预期空间充足**：华尔街机构中位数目标价为 ${target_median:.2f}，隐含 {upside_pct:+.1f}% 上行空间。")
    else:
        pros.append(f"**资金关注度高**：所属细分赛道具备产业趋势红利，机构筹码结构相对稳定。")

    # 4. 提取 3 条核心不推荐理由（风险提示）
    cons = []
    if pe and pe > 35:
        cons.append(f"**估值容错率低**：前瞻 PE 达到 {pe:.1f} 倍，市场预期极高，财报稍有不及预期容易引发剧烈回调。")
    else:
        cons.append(f"**估值重估缺乏催化**：当前估值倍数平淡，需要更强劲的增量业务才能打开上升空间。")

    if short_ratio and short_ratio > 4.0:
        cons.append(f"**空头对冲压力较重**：空头回补天数 (Short Ratio) 为 {short_ratio:.1f}，存在一定的机构做空对冲压力。")
    else:
        cons.append(f"**宏观敏感度较高**：利率环境与整体科技/大盘风险偏好变动容易对股价产生波及。")

    cons.append(f"**竞争与技术替代风险**：行业竞争加剧可能导致未来营销开支上升或净利率承压。")

    # 5. 计算量化止损证伪红线
    stop_loss_price = max(fifty_low, c_price * 0.88)
    stop_loss = f"若股价放量跌破关键技术支撑位 **${stop_loss_price:.2f}**（或下季度营收增速断崖跌破 10%），说明上行逻辑失效，需严格执行止损。"

    return {
        "verdict": verdict,
        "short_bias": short_bias,
        "horizon": horizon,
        "summary": f"基于最新财务指标量化综合打分：{score}/100 分。毛利率 {gross_margin*100:.1f}%，增速 {rev_growth*100:.1f}%。",
        "pros": pros,
        "cons": cons,
        "stop_loss": stop_loss
    }

# ================= 4. 界面渲染 =================
st.markdown("### 🧭 ReasonVest 美股量化决策终端")

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
    manual_search = st.text_input("或直接搜索任意代码:", placeholder="如 NVDA, AMD, SOFI").upper().strip()

current_ticker = manual_search if manual_search else selected_ticker

st.markdown("---")

try:
    with st.spinner(f"正在加载 {current_ticker}..."):
        stock_info, hist_data, financials = fetch_stock_details(current_ticker)
        c_price = stock_info.get("currentPrice") or stock_info.get("regularMarketPrice", 0.0)
        p_close = stock_info.get("previousClose", c_price)
        pct = ((c_price - p_close) / p_close * 100) if p_close else 0.0
except Exception as e:
    st.error(f"代码输入有误或数据拉取失败: {e}")
    st.stop()

# 顶部个股卡片
st.markdown(f"""
<div class="mobile-card">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <h2 style="margin:0; padding:0;">{stock_info.get('shortName', current_ticker)} ({current_ticker})</h2>
            <span style="color:#8b949e; font-size:13px;">{stock_info.get('sector', '未知行业')} · {stock_info.get('industry', '')}</span>
        </div>
        <div style="text-align:right;">
            <h2 style="margin:0; padding:0;">${c_price:.2f}</h2>
            <span style="color:{'#26a69a' if pct>=0 else '#ef5350'}; font-weight:bold;">{pct:+.2f}%</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

tab_reason, tab_chart, tab_fin = st.tabs(["🧠 决策推导 (免Key)", "📈 走势图", "📑 财报数据"])

# ------------ TAB 1: 免 API Key 量化推理 ------------
with tab_reason:
    st.write("点击下方按钮，系统将**直接运行量化逻辑**，推导演绎多空对抗分析：")
    
    if st.button("🚀 运行针对该标的的量化推理", type="primary", use_container_width=True):
        data = run_quant_reasoning(stock_info, c_price)

        v_color = "🟢" if ("推荐" in data['verdict'] or "买入" in data['verdict']) else ("🔴" if "规避" in data['verdict'] else "🟡")
        bias_badge = "🚀 看涨" if data['short_bias'] == "看涨" else ("📉 看跌" if data['short_bias'] == "看跌" else "⚖️ 震荡")

        st.markdown(f"""
        <div class="mobile-card">
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span>综合投资评价: <b>{v_color} {data['verdict']}</b></span>
                <span>短期视角 (1-3月): <b>{bias_badge}</b></span>
            </div>
            <p style="margin:4px 0; font-size:14px; color:#e6edf3;"><b>综合定量评价</b>: {data['summary']}</p>
            <p style="margin:4px 0; font-size:13px; color:#8b949e;"><b>短期走势推演</b>: {data['horizon']}</p>
        </div>
        """, unsafe_allow_html=True)

        st.success("### ✅ 为什么推荐它 (做多驱动)")
        for p in data['pros']:
            st.markdown(p)

        st.error("### ❌ 为什么不推荐它 (核心风险)")
        for c in data['cons']:
            st.markdown(c)

        st.warning(f"🚨 **逻辑证伪红线**：{data['stop_loss']}")

# ------------ TAB 2: 走势图 ------------
with tab_chart:
    if not hist_data.empty:
        fig = go.Figure(data=[go.Candlestick(
            x=hist_data.index,
            open=hist_data['Open'], high=hist_data['High'],
            low=hist_data['Low'], close=hist_data['Close']
        )])
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=320,
            margin=dict(l=5, r=5, t=10, b=10),
            template="plotly_dark"
        )
        st.plotly_ch
