from __future__ import annotations

import streamlit as st

MIN_TEXT_LENGTH = 50
MAX_TEXT_LENGTH = 4000
MIN_WORD_COUNT = 30


def render_job_description_input() -> tuple[str, bool]:
    st.subheader("Enter the Job Description")
    raw_text = st.text_area(
        "Job Description (English)",
        height=280,
        placeholder="Type or paste the full English job description here...",
        help=(
            "The text must be between 50 and 4000 characters and contain at least 30 words."
        ),
    )

    normalized_text = raw_text.strip()
    char_count = len(normalized_text)
    word_count = len(normalized_text.split()) if normalized_text else 0

    st.caption(
        f"Characters: {char_count}/{MAX_TEXT_LENGTH} | Words: {word_count}/{MIN_WORD_COUNT}+"
    )

    if normalized_text:
        if char_count < MIN_TEXT_LENGTH:
            st.error(
                f"The job description is too short. Minimum length is {MIN_TEXT_LENGTH} characters before submission."
            )
        elif char_count > MAX_TEXT_LENGTH:
            st.error(
                f"The job description is too long. Maximum length is {MAX_TEXT_LENGTH} characters before submission."
            )

        if word_count < MIN_WORD_COUNT:
            st.error(
                f"The job description must contain at least {MIN_WORD_COUNT} words before submission."
            )

    is_valid = (
        MIN_TEXT_LENGTH <= char_count <= MAX_TEXT_LENGTH
        and word_count >= MIN_WORD_COUNT
    )
    submitted = st.button(
        "Parse Job Description",
        type="primary",
        disabled=not is_valid,
    )

    return normalized_text, submitted
