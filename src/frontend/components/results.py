from __future__ import annotations

from typing import Any

import streamlit as st


def render_parse_response(response_payload: dict[str, Any]) -> None:
    signal = str(response_payload.get("signal", ""))
    processing_time_ms = response_payload.get("processing_time_ms")
    job_details = response_payload.get("data")

    if "fallback" in signal.lower():
        st.warning(signal)
    else:
        st.success(signal or "Parsing completed.")

    if isinstance(processing_time_ms, int):
        st.caption(f"Processing time: {processing_time_ms} ms")

    if not isinstance(job_details, dict):
        st.error("The backend response does not include valid JobDetails data.")
        return

    st.subheader("Parsed JobDetails")
    st.json(job_details, expanded=True)
