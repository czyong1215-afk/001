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

@st.cache_data(ttl=300)
def fetch_stock_details(ticker):
    """安全拉取单只股票详情，保证返回有效对象"""
    stock = yf.Ticker(ticker)
    info = stock.info or {}
    
    # 稳健获取K线数据
    try:
        hist = stock.history(period="6mo")
    except:
        hist = pd.DataFrame()
        
    # 稳健获取财报数据
    try:
        fin = stock.financials
        if fin is None:
            fin = pd.DataFrame()
    except:
        fin = pd.DataFrame()

    return info, hist, fin

# ================= 3. 核心量化推理算法 =================
def run_quant_reasoning(info, c_price):
    rev_growth = info.get("revenueGrowth", 0) or 0
    gross_margin = info.get("grossMargins", 0) or 0
    pe = info.get("forwardPE", 0) or 0
    target_median = info.get("targetMedianPrice", c_price) or c_price
    short_ratio = info.get("shortRatio", 0) or 0
    fifty_low = info.get("fiftyTwoWeekLow", c_price * 0.7) or (c_price * 0.7)

    upside_pct = ((target_median - c_price) / c_price * 100) if c_price else 0

    score = 50
    if rev_growth > 0.25: score += 20
    elif rev_growth > 0.10: score += 10
    elif rev_growth < 0: score -= 20

    if gross_margin > 0.50: score += 15
    elif gross_margin < 0.20: score -= 15

    if upside_pct > 20: score += 15
    elif upside_pct < 0: score -= 15

    if pe and pe > 60: score -= 10

    if score >= 75:
        verdict = "强烈推荐"
        short_bias = "看涨"
        horizon = f"机构一致目标价空间达 {upside_pct:+.1f}%，高增长有望持续催化估值重估。"
    elif score >= 60:
        verdict = "逢低买入"
        short_bias = "看涨"
        horizon = "基本面健康，现价具备合理安全边际，短期以震荡上行为主。"
    elif score >= 45:
        verdict = "谨慎观望"
        short_bias = "震荡"
        horizon = "当前估值已充分计入业绩，短期缺乏超预期催化剂，建议等待回调。"
    else:
        verdict = "建议规避"
        short_bias = "看跌"
        horizon = "基本面增速承压或估值偏高，短期存在均值回归回调压力。"

    pros = []
    if rev_growth > 0.15:
        pros.append(f"**业绩爆发力强**：最新营收同比增速达 {rev_growth*100:.1f}%，领跑赛道。")
    else:
        pros.append(f"**现金流稳健**：核心业务抗风险能力强，具备成熟运营壁垒。")

    if gross_margin > 0.40:
        pros.append(f"**产品定价权强**：毛利率达 {gross_margin*100:.1f}%，具备较深产业护城河。")
    else:
        pros.append(f"**赛道放量中**：受益于行业渗透率提升，规模化优势初显。")

    if upside_pct > 0:
        pros.append(f"**目标空间充足**：分析师中位数目标价为 ${target_median:.2f}，潜在空间 {upside_pct:+.1f}%。")
    else:
        pros.append(f"**机构筹码稳定**：主力资金关注度高，流动性极佳。")

    cons = []
    if pe and pe > 35:
        cons.append(f"**估值容错率低**：前瞻 PE 达 {pe:.1f}x，若下季财报指引轻微不及预期，易引发回撤。")
    else:
        cons.append(f"**增量催化不足**：估值中枢相对平稳，需新产品线放量方可打破震荡。")

    if short_ratio and short_ratio > 3.0:
        cons.append(f"**空头对冲压力**：空头回补天数为 {short_ratio:.1f} 天，存在阶段性做空博弈。")
    else:
        cons.append(f"**宏观波动传导**：容易受美联储利率政策与科技大盘情绪联动扰动。")

    cons.append(f"**竞争替代风险**：行业竞争激烈，需持续关注核心大客户流失风险。")

    stop_loss_price = max(fifty_low, c_price * 0.88)
    stop_loss = f"若股价放量跌破技术支撑位 **${stop_loss_price:.2f}**（或下季营收增速断崖跌破 10%），说明上行逻辑破坏，需坚决止损。"

    return {
        "verdict": verdict,
        "short_bias": short_bias,
        "horizon": horizon,
        "summary": f"量化评分: {score}/100。毛利率: {gross_margin*100:.1f}%, 增速: {rev_growth*100:.1f}%。",
        "pros": pros,
        "cons": cons,
        "stop_loss": stop_loss
    }

# ================= 4. 主界面交互 =================
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
    manual_search = st.text_input("或直接搜索任意美股代码:", placeholder="如 NVDA, AMD, SOFI").upper().strip()

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

# 顶部核心信息条
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

tab_reason, tab_chart, tab_fin = st.tabs(["🧠 量化决策推导", "📈 实时K线走势", "📑 财报明细数据"])

# ------------ TAB 1: 免 API Key 量化推理 ------------
with tab_reason:
    st.write("点击下方按钮，系统将**直接运行量化逻辑**推导多空对抗分析：")
    
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

# ------------ TAB 2: 防崩溃 K 线走势图 ------------
with tab_chart:
    st.caption("近 6 个月行情走势（支持手指双指缩放查看细节）")
    if not hist_data.empty and len(hist_data) > 1:
        try:
            # 清洗时间戳时区，避免前端解析成空白
            dates = pd.to_datetime(hist_data.index).strftime('%Y-%m-%d')
            
            fig = go.Figure()
            # 绘制专业蜡烛图 K 线
            fig.add_trace(go.Candlestick(
                x=dates,
                open=hist_data['Open'],
                high=hist_data['High'],
                low=hist_data['Low'],
                close=hist_data['Close'],
                name="K线"
            ))
            fig.update_layout(
                xaxis_rangeslider_visible=False,
                height=350,
                margin=dict(l=5, r=5, t=10, b=10),
                template="plotly_dark",
                paper_bgcolor="#181b26",
                plot_bgcolor="#181b26"
            )
            # 正确完整的绘图调用
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            # 万一蜡烛图绘制遇到极端数据，自动降级为折线图，确保绝对有图
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(x=hist_data.index, y=hist_data['Close'], mode='lines', name='收盘价', line=dict(color='#26a69a', width=2)))
            fig_line.update_layout(height=350, template="plotly_dark", margin=dict(l=5, r=5, t=10, b=10))
            st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.warning("⚠️ 暂未获取到近期交易日 K 线数据（可能为周末休市或网络延迟），请稍后重试。")

# ------------ TAB 3: 深度财报明细数据 ------------
with tab_fin:
    st.markdown("#### 核心财务健康度")
    fc1, fc2 = st.columns(2)
    fc1.metric("毛利率 (Gross Margin)", f"{(stock_info.get('grossMargins', 0) or 0) * 100:.1f}%")
    fc2.metric("净利率 (Profit Margin)", f"{(stock_info.get('profitMargins', 0) or 0) * 100:.1f}%")
    
    fc3, fc4 = st.columns(2)
    fc3.metric("营收同比增速 (YoY)", f"{(stock_info.get('revenueGrowth', 0) or 0) * 100:.1f}%")
    fc4.metric("动态市盈率 (Forward PE)", f"{stock_info.get('forwardPE', 'N/A')}")

    st.markdown("---")
    st.markdown("#### 最新年度损益表核心明细 (单位: 百万美元)")
    
    if not financials.empty:
        try:
            # 过滤只显示主要财务条目
            clean_fin = financials.copy()
            # 将列名格式化为年份
            clean_fin.columns = [pd.to_datetime(c).strftime('%Y年') for c in clean_fin.columns]
            
            # 安全转为数值型，防止字符串造成崩溃
            clean_fin = clean_fin.apply(pd.to_numeric, errors='coerce').fillna(0)
            clean_fin = clean_fin / 1e6 # 换算为百万美元

            # 筛选投资者最关注的核心财务科目
            key_index = [idx for idx in clean_fin.index if any(k in str(idx) for k in [
                'Total Revenue', 'Operating Revenue', 'Cost Of Revenue', 'Gross Profit', 
                'Operating Income', 'Net Income', 'EBITDA'
            ])]
            
            if key_index:
                display_df = clean_fin.loc[key_index]
            else:
                display_df = clean_fin.head(6)

            st.dataframe(display_df.style.format("{:,.1f}"), use_container_width=True)
        except Exception:
            st.info("财报明细表格正在同步中，上方财务指标已是最新状态。")
    else:
        st.info("该标的暂时没有公开详细年度损益表，可直接参考上方的核心财务比率。")
