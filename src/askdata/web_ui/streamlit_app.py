"""AskData Streamlit UI — chat-style interface over the NL2SQL agent."""
import os
import sys

import pandas as pd
import streamlit as st

# Allow `python -m streamlit run` from project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from askdata.agent.nl2sql_agent import NL2SQLAgent  # noqa: E402
from askdata.llm_client import LLMClient  # noqa: E402

st.set_page_config(page_title="AskData", page_icon="💬", layout="wide")
st.title("💬 AskData — 一句话查全公司数据")


@st.cache_resource
def get_agent() -> NL2SQLAgent:
    llm = LLMClient()
    return NL2SQLAgent(llm=llm, datasource="postgres")


with st.sidebar:
    st.header("⚙️ 配置")
    st.markdown("**数据源**: `postgres`")
    st.markdown("**LLM**: 见 `.env` 中的 `LLM_PROVIDER`")
    if st.button("🧹 清空对话"):
        st.session_state.messages = []
        st.rerun()

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
            st.plotly_chart(msg["chart"], use_container_width=True)

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
            st.session_state.messages.append({"role": "assistant", "content": result["error"]})
        else:
            st.markdown(result["explanation"] or "(无解释)")
            df = pd.DataFrame(result["results"])
            st.dataframe(df, use_container_width=True)
            chart = None
            if not df.empty and len(df.columns) >= 2:
                try:
                    import plotly.express as px

                    chart = px.bar(df, x=df.columns[0], y=df.columns[1])
                except Exception:
                    chart = None
            if chart is not None:
                st.plotly_chart(chart, use_container_width=True)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": result["explanation"] or "(无解释)",
                    "sql": result["sql"],
                    "df": df,
                    "chart": chart,
                }
            )
