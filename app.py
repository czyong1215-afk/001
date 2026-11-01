import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from openai import OpenAI
import json
import re

# ================= 1. 移动端原生视口与主题注入 =================
st.set_page_config(
    page_title="ReasonVest - 美股AI推理终端",
    page_icon="📈",
    layout="centered", # 针对手机竖屏优化的居中流式布局
    initial_sidebar_state="collapsed"
)

# 注入移动端专用 CSS：大圆角卡片、触摸优化、沉浸式 OLED 黑色背景
st.markdown("""
<style>
    /* 隐藏 Streamlit 默认的顶部多余白边和页脚 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    /* 移动端卡片风格 */
    .mobile-card {
        background: #181b26;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 12px;
        border: 1px solid #282d3f;
    }
    .badge-bull {
        background-color: rgba(38, 166, 154, 0.2);
        color: #26a69a;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: bold;
    }
    .badge-bear {
        background-color: rgba(239, 83, 80, 0.2);
        color: #ef5350;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: bold;
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
    # 能源变革与周期反转
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

# ================= 3. 顶部移动端折叠设置（避免左侧栏） =================
st.markdown("### 🧭 ReasonVest 美股决策终端")

with st.expander("⚙️ 引擎配置 (API Key 设置)", expanded=False):
    api_key = st.text_input("LLM API Key (支持 DeepSeek / OpenAI):", type="password")
    base_url = st.text_input("Base URL (如使用 DeepSeek 填写 https://api.deepseek.com):", value="")
    model_name = st.selectbox("选择模型:", ["deepseek-chat", "gpt-4o", "gpt-4o-mini"])

# ================= 4. 移动端快捷选股与分类筛选 =================
category_filter = st.radio(
    "板块分类切换",
    ["🔥 潜力黑马股", "💻 科技龙头", "全部股票池"],
    horizontal=True
)

with st.spinner("刷新市场数据..."):
    df_screener = fetch_screener_data()

# 根据分类筛选
if category_filter == "🔥 潜力黑马股":
    df_show = df_screener[df_screener["分类"] == "🔥潜力黑马"]
elif category_filter == "💻 科技龙头":
    df_show = df_screener[df_screener["分类"] == "科技巨头"]
else:
    df_show = df_screener

# 手机表格展示
st.dataframe(
    df_show[["Ticker", "名称", "现价($)", "营收增速", "毛利率", "前瞻PE"]],
    use_container_width=True,
    hide_index=True
)

# 手动检索或点击选择
col_search1, col_search2 = st.columns([1, 1])
with col_search1:
    selected_from_list = st.selectbox("从列表中选定标的:", df_show["Ticker"].tolist())
with col_search2:
    manual_search = st.text_input("或直接搜索 Ticker:", placeholder="如 AMD, SOFI").upper().strip()

current_ticker = manual_search if manual_search else selected_from_list

# ================= 5. 单股详情与多空推理 =================
st.markdown("---")

try:
    with st.spinner(f"拉取 {current_ticker} 深度数据..."):
        stock_info, hist_data, financials = fetch_stock_details(current_ticker)
        c_price = stock_info.get("currentPrice") or stock_info.get("regularMarketPrice", 0.0)
        p_close = stock_info.get("previousClose", c_price)
        pct = ((c_price - p_close) / p_close * 100) if p_close else 0.0
except Exception as e:
    st.error(f"代码输入有误或数据拉取失败: {e}")
    st.stop()

# 股票核心信息条（适合手机屏）
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

# 移动端标签页切换
tab_ai, tab_chart, tab_fin = st.tabs(["🧠 AI 多空推理", "📈 走势图", "📑 财报数据"])

# ------------ TAB 1: AI 多空推理 (核心功能) ------------
with tab_ai:
    st.write("点击按钮，大模型将直接生成**评级、短期看涨/看跌、推荐与不推荐理由**：")
    
    if st.button("🚀 生成针对该股票的 AI 投资推理", type="primary", use_container_width=True):
        if not api_key:
            st.warning("⚠️ 请先在顶部的【⚙️ 引擎配置】中填入 API Key！")
        else:
            client_args = {"api_key": api_key}
            if base_url:
                client_args["base_url"] = base_url
            client = OpenAI(**client_args)

            prompt = f"""
            你是一名华尔街顶级对冲基金的投资决策总监。请根据以下标的数据进行严格的多空对抗投资逻辑推导。
            严禁给出模糊中庸的回答，必须明确给出短期看涨还是看跌，并同时给出充分的推荐理由与不推荐理由。

            【标的数据】
            - 标的代码: {current_ticker} ({stock_info.get('shortName')})
            - 现价: ${c_price} | 52周区间: ${stock_info.get('fiftyTwoWeekLow')} - ${stock_info.get('fiftyTwoWeekHigh')}
            - 预期PE: {stock_info.get('forwardPE')} | 营收增速(YoY): {stock_info.get('revenueGrowth')} | 毛利率: {stock_info.get('grossMargins')}
            - 分析师目标价中位数: ${stock_info.get('targetMedianPrice')}
            - 业务简述: {stock_info.get('longBusinessSummary', '')[:350]}...

            请严格按照以下 JSON 格式输出，不要输出任何额外的解释或 markdown 符号：
            {{
              "verdict": "强烈推荐 / 逢低买入 / 谨慎观望 / 建议规避 (四选一)",
              "short_bias": "看涨 / 看跌 / 震荡 (三选一)",
              "horizon_rationale": "说明未来 1-3 个月看涨或看跌的核心催化事件",
              "summary": "一句话精准定性评价",
              "pros": [
                "推荐理由1：最核心的业绩爆发驱动",
                "推荐理由2：技术护城河或行业红利",
                "推荐理由3：估值安全性或催化剂"
              ],
              "cons": [
                "不推荐理由1：最致命的业务缺陷或估值承压点",
                "不推荐理由2：财报暴雷隐患或客户流失风险",
                "不推荐理由3：宏观逆风或竞对冲击"
              ],
              "stop_loss": "出现什么具体的量化指标恶化（如毛利率跌破X%、大客户流失）时看多逻辑彻底破产，必须止损"
            }}
            """

            with st.spinner("AI 投资总监正在构建逻辑因果树与逆向测试..."):
                try:
                    res = client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2
                    )
                    content = res.choices[0].message.content.strip()
                    cleaned = re.sub(r"^```json\s*", "", content)
                    cleaned = re.sub(r"\s*```$", "", cleaned)
                    data = json.loads(cleaned)

                    # 1. 顶部综评看板
                    v_color = "🟢" if ("推荐" in data['verdict'] or "买入" in data['verdict']) else ("🔴" if "规避" in data['verdict'] else "🟡")
                    bias_badge = "🚀 看涨" if data['short_bias'] == "看涨" else ("📉 看跌" if data['short_bias'] == "看跌" else "⚖️ 震荡")

                    st.markdown(f"""
                    <div class="mobile-card">
                        <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                            <span>综合评级: <b>{v_color} {data['verdict']}</b></span>
                            <span>短期视角 (1-3月): <b>{bias_badge}</b></span>
                        </div>
                        <p style="margin:4px 0; font-size:14px; color:#e6edf3;"><b>一句话综评</b>: {data['summary']}</p>
                        <p style="margin:4px 0; font-size:13px; color:#8b949e;"><b>短期推演</b>: {data['horizon_rationale']}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # 2. 为什么推荐 vs 为什么不推荐
                    st.success("### ✅ 为什么推荐它 (做多驱动)")
                    for idx, p in enumerate(data.get("pros", []), 1):
                        st.markdown(f"**{idx}.** {p}")

                    st.error("### ❌ 为什么不推荐它 (核心风险)")
                    for idx, c in enumerate(data.get("cons", []), 1):
                        st.markdown(f"**{idx}.** {c}")

                    # 3. 止损证伪红线
                    st.warning(f"🚨 **逻辑证伪红线**：{data.get('stop_loss')}")

                except Exception as ex:
                    st.error(f"推理引擎解析失败: {ex}")

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
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无历史走势数据。")

# ------------ TAB 3: 财报数据 ------------
with tab_fin:
    fc1, fc2 = st.columns(2)
    fc1.metric("毛利率", f"{(stock_info.get('grossMargins', 0) or 0) * 100:.1f}%")
    fc2.metric("净利率", f"{(stock_info.get('profitMargins', 0) or 0) * 100:.1f}%")
    fc3, fc4 = st.columns(2)
    fc3.metric("营收增速", f"{(stock_info.get('revenueGrowth', 0) or 0) * 100:.1f}%")
    fc4.metric("动态PE", f"{stock_info.get('forwardPE', 'N/A')}")
