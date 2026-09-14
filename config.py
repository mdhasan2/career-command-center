from __future__ import annotations

from typing import Any
import streamlit as st
from drive_client import DriveClient

CHAKORI_SPREADSHEET_ID = "1EHWvTharEba2L3dEeyN31MElWbaH-o83AcnNK7SD2ZA"
CHAKORI_SHEET_NAME = "Company Tracker"


def _to_plain_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return dict(value)


@st.cache_resource(show_spinner=False)
def build_drive_client() -> DriveClient | None:
    try:
        info = _to_plain_dict(st.secrets["google_service_account"])
    except (KeyError, FileNotFoundError):
        return None
    return DriveClient(info)
