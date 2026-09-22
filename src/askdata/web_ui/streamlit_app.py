"""AskData Streamlit UI — chat-style interface over the NL2SQL agent.

Renders the chart recommendation returned by the agent (line / bar / pie /
scatter / kpi_card / table / empty).
"""
import os
import sys

import pandas as pd
import streamlit as st

# Allow `python -m streamlit run` from project root.
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from askdata.agent.nl2sql_agent import NL2SQLAgent  # noqa: E402
from askdata.llm_client import LLMClient  # noqa: E402
from askdata.tools.chart_recommender import recommend_chart  # noqa: E402

st.set_page_config(page_title="AskData", page_icon="💬", layout="wide")
st.title("💬 AskData — 一句话查全公司数据")


@st.cache_resource
def get_agent() -> NL2SQLAgent:
    llm = LLMClient()
    return NL2SQLAgent(llm=llm, datasource="postgres")


def _render_chart(df: pd.DataFrame, chart: dict) -> None:
    """根据 chart_recommender 的推荐画图。"""
    chart_type = chart.get("chart_type", "table")
    x, y = chart.get("x"), chart.get("y")

    if chart_type == "empty":
        st.info("🔍 查询无结果。")
        return
    if df.empty:
        return

    import plotly.express as px

    if chart_type == "kpi_card":
        val = df[y if y else df.columns[0]].iloc[0] if y in df.columns else None
        st.metric(label=y or df.columns[0], value=val)
        return

    if chart_type == "line" and x in df.columns and y in df.columns:
        st.plotly_chart(px.line(df, x=x, y=y), use_container_width=True)
    elif chart_type == "bar" and x in df.columns and y in df.columns:
        st.plotly_chart(px.bar(df, x=x, y=y), use_container_width=True)
    elif chart_type == "pie" and x in df.columns and y in df.columns:
        st.plotly_chart(px.pie(df, names=x, values=y), use_container_width=True)
    elif chart_type == "scatter" and x in df.columns and y in df.columns:
        st.plotly_chart(px.scatter(df, x=x, y=y), use_container_width=True)
    else:
        st.dataframe(df, use_container_width=True)


# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("⚙️ 配置")
    st.markdown("**数据源**: `postgres`")
    st.markdown("**LLM**: 见 `.env` 中的 `LLM_PROVIDER`")
    if st.button("🧹 清空对话"):
        st.session_state.messages = []
        st.rerun()

# ---------- 历史消息 ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sql" in msg:
            with st.expander("🔍 生成的 SQL"):
                st.code(msg["sql"], language="sql")
        if "df" in msg and msg["df"] is not None and not msg["df"].empty:
            st.dataframe(msg["df"], use_container_width=True)
        if "chart" in msg and msg["chart"] is not None:
            _render_chart(msg["df"], msg["chart"])

# ---------- 输入 ----------
if prompt := st.chat_input("用一句话提问,例如:Q3 华东区大客户复购率多少?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Agent 正在检索表结构、生成 SQL、执行查询…"):
            try:
                agent = get_agent()
                result = agent.run(prompt)
            except Exception as exc:
                st.error(f"❌ {exc}")
                st.stop()

        if "error" in result:
            st.error(result["error"])
            with st.expander("🔍 尝试过的 SQL"):
                st.code(result.get("sql", ""), language="sql")
            st.session_state.messages.append(
                {"role": "assistant", "content": result["error"]}
            )
        else:
            explanation = result.get("explanation") or "(无解释)"
            st.markdown(explanation)
            df = pd.DataFrame(result["results"])
            chart = result.get("chart") or recommend_chart(result["results"])
            st.dataframe(df, use_container_width=True)
            _render_chart(df, chart)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": explanation,
                    "sql": result["sql"],
                    "df": df,
                    "chart": chart,
                }
            )
