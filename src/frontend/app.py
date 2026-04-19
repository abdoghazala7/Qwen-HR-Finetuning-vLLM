from __future__ import annotations

import streamlit as st

from components.input_form import render_job_description_input
from components.results import render_parse_response
from services.api_client import (
    ParserAPIClientError,
    check_api_health,
    fetch_job_schema,
    parse_job_description,
)

st.set_page_config(
    page_title="English Job Description Parser",
    page_icon="🧠",
    layout="wide",
)

st.title("English Job Description Parser")
st.write(
    "Use this interface to parse and normalize English job descriptions into a structured JobDetails response."
)
st.caption("Note: This parser is fine-tuned for English job descriptions only.")

st.sidebar.header("Developer Tools")

if check_api_health():
    st.sidebar.success("🟢 Backend API: Online")
else:
    st.sidebar.error("🔴 Backend API: Offline")

with st.sidebar.expander("📄 View Target Schema"):
    schema_payload = fetch_job_schema()
    if schema_payload is None:
        st.warning("Target schema could not be loaded.")
    else:
        st.json(schema_payload)

job_description, submitted = render_job_description_input()

if submitted:
    with st.spinner("Parsing job description..."):
        try:
            response_payload = parse_job_description(job_description)
        except ParserAPIClientError as exc:
            st.error(str(exc))
        else:
            render_parse_response(response_payload)
