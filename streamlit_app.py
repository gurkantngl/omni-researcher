import streamlit as st

from omni_analyst.app import run
from omni_analyst.agents.reporter import build_comparison_table


st.set_page_config(page_title="Omni-Analyst", layout="wide")
st.title("Omni-Analyst")

default_question = (
    "NVIDIA'nin son ceyrek raporunu analiz et, rakipleriyle karsilastir "
    "ve riskleri ozetle."
)
question = st.text_area(
    "Arastirma sorusu",
    value=default_question,
    height=120,
)

run_clicked = st.button("Analizi calistir", type="primary")
if run_clicked:
    with st.spinner("Arastirma yapiliyor..."):
        result = run(question)
    st.session_state["result"] = result

result = st.session_state.get("result")
if result:
    st.subheader("Karsilastirma Tablosu")
    st.markdown(build_comparison_table(result))

    st.subheader("Rapor")
    st.markdown(result["final_report"])

    with st.expander("Ham ciktilar"):
        st.write(result.get("draft_report", ""))
        st.write(result.get("documents", []))
        st.write(result.get("extracted_tables", []))
