from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd
import streamlit as st

from config import build_drive_client, LAUNCHPAD_SHEET_NAME, LAUNCHPAD_SPREADSHEET_ID

st.set_page_config(page_title="Career Command Center", page_icon="🎯", layout="wide")

COLUMN_MAP = {
    "Company": "employer",
    "Role": "job_title",
    "Open Role": "open_role",
    "Location": "location",
    "Source": "source",
    "Fit Score": "fit_score",
    "Base Pay Min": "base_pay_min",
    "Base Pay Max": "base_pay_max",
    "Attention Score": "attention_score",
    "Connection Established?": "connection_established",
    "Connection Name": "connection_name",
    "Applied?": "applied",
    "Benefits": "benefits",
    "Job URL": "job_url",
    "Posted / Age": "posted",
    "Closing Date": "closing_date",
    "Attention Factors": "attention_factors",
    "Employer Type": "employer_type",
    "Application Status": "status",
    "Next Action": "next_action",
    "Notes": "notes",
}


def _clean(v: Any) -> Any:
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    return v


def _to_number(v: Any) -> float | None:
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def money(v: Any) -> str:
    n = _to_number(v)
    return "Not stated" if n is None else f"${n:,.0f}"


def parse_date(v: Any) -> date | None:
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return pd.to_datetime(v).date()
    except Exception:
        return None


def calculate_attention(row: dict[str, Any]) -> tuple[int, str]:
    fit = _to_number(row.get("fit_score")) or 0
    fit_pts = fit * 0.40

    employer_type = str(row.get("employer_type", "")).lower()
    if "private" in employer_type:
        sector_pts = 15
    elif "government contractor" in employer_type or "professional services" in employer_type:
        sector_pts = 7
    else:
        sector_pts = 0

    location = str(row.get("location", "")).lower()
    if "remote" in location:
        location_pts = 15
    elif any(x in location for x in ["augusta", "martinez", "fort eisenhower", "greater augusta"]):
        location_pts = 12
    else:
        location_pts = 0

    pay_min = _to_number(row.get("base_pay_min"))
    pay_max = _to_number(row.get("base_pay_max"))
    if pay_min is not None and pay_min >= 180000:
        comp_pts = 15
    elif pay_max is not None and pay_max >= 180000:
        comp_pts = 9
    elif pay_min is None and pay_max is None:
        comp_pts = 4
    else:
        comp_pts = 0

    connection_pts = 5 if str(row.get("connection_established", "")).strip().lower() == "yes" else 0
    application_pts = 0 if str(row.get("applied", "")).strip().lower() == "yes" else 5

    urgency_pts = 1
    closing = parse_date(row.get("closing_date"))
    if closing:
        days = (closing - date.today()).days
        if days <= 3:
            urgency_pts = 5
        elif days <= 7:
            urgency_pts = 4
        elif days <= 14:
            urgency_pts = 2

    total = round(fit_pts + sector_pts + location_pts + comp_pts + connection_pts + application_pts + urgency_pts)
    factors = (
        f"Fit {fit_pts:g} | Sector {sector_pts} | Location {location_pts} | "
        f"Comp {comp_pts} | Connection {connection_pts} | Unapplied {application_pts} | Urgency {urgency_pts}"
    )
    return total, factors


@st.cache_data(ttl=300, show_spinner=False)
def load_jobs() -> tuple[list[dict[str, Any]], str]:
    client = build_drive_client()
    if client is None:
        return [], "Launchpad unavailable: Streamlit secrets are not configured."
    try:
        values = client.read_sheet_values(LAUNCHPAD_SPREADSHEET_ID, LAUNCHPAD_SHEET_NAME)
    except Exception as exc:
        return [], f"Launchpad read failed: {exc}"
    if not values:
        return [], "Launchpad returned no rows."

    headers = [str(x).strip() for x in values[0]]
    jobs: list[dict[str, Any]] = []
    for raw in values[1:]:
        padded = list(raw) + [""] * max(0, len(headers) - len(raw))
        source_row = {headers[i]: _clean(padded[i]) for i in range(len(headers))}
        fit = _to_number(source_row.get("Fit Score"))
        source = str(source_row.get("Source", ""))
        if fit is None or ("Job Search" not in source and not source_row.get("Job URL")):
            continue

        row = {dest: source_row.get(src, "") for src, dest in COLUMN_MAP.items()}
        row["job_title"] = row.get("job_title") or row.get("open_role") or "Untitled role"
        row["fit_score"] = int(fit)
        row["base_pay_min"] = _to_number(row.get("base_pay_min"))
        row["base_pay_max"] = _to_number(row.get("base_pay_max"))
        sheet_attention = _to_number(row.get("attention_score"))
        calc_attention, factors = calculate_attention(row)
        row["attention_score"] = int(sheet_attention) if sheet_attention is not None else calc_attention
        row["attention_factors"] = row.get("attention_factors") or factors
        jobs.append(row)

    jobs.sort(key=lambda x: (-int(x.get("attention_score", 0)), -int(x.get("fit_score", 0))))
    return jobs, f"Launchpad → {LAUNCHPAD_SHEET_NAME}"


jobs, source_label = load_jobs()

st.title("🎯 Career Command Center")
st.caption(f"Source of truth: {source_label}")

if not jobs:
    st.warning(source_label)
    st.stop()

with st.sidebar:
    st.header("Filters")
    min_fit = st.slider("Minimum fit", 0, 100, 70, 5)
    min_attention = st.slider("Minimum attention", 0, 100, 0, 5)
    employer_types = sorted({str(j.get("employer_type", "")) for j in jobs if j.get("employer_type")})
    selected_types = st.multiselect("Employer type", employer_types, default=employer_types)
    page = st.radio("Navigate", ["Today", "Top Matches", "Pipeline"])
    if st.button("Refresh Launchpad"):
        st.cache_data.clear()
        st.rerun()

filtered = [
    j for j in jobs
    if int(j.get("fit_score", 0)) >= min_fit
    and int(j.get("attention_score", 0)) >= min_attention
    and (not selected_types or j.get("employer_type") in selected_types)
]

if page == "Today":
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Tracked jobs", len(filtered))
    c2.metric("Attention 85+", sum(1 for j in filtered if j.get("attention_score", 0) >= 85))
    c3.metric("Fit 90+", sum(1 for j in filtered if j.get("fit_score", 0) >= 90))
    c4.metric("Connections", sum(1 for j in filtered if str(j.get("connection_established", "")).lower() == "yes"))
    c5.metric("Applied", sum(1 for j in filtered if str(j.get("applied", "")).lower() == "yes"))

    st.subheader("Attention Queue")
    for j in filtered[:8]:
        with st.container(border=True):
            st.markdown(f"### {j.get('attention_score', 0)}/100 Attention · {j.get('fit_score', 0)}/100 Fit — {j.get('job_title')} · {j.get('employer')}")
            a, b, c, d = st.columns(4)
            a.write(f"**Location**  \n{j.get('location') or 'Not stated'}")
            b.write(f"**Compensation**  \n{money(j.get('base_pay_min'))} – {money(j.get('base_pay_max'))}")
            c.write(f"**Connection**  \n{j.get('connection_established') or 'No'}")
            d.write(f"**Applied**  \n{j.get('applied') or 'No'}")
            st.write(f"**Connection name:** {j.get('connection_name') or 'None recorded'}")
            st.write(f"**Next action:** {j.get('next_action') or 'Not stated'}")
            st.caption(j.get("attention_factors") or "")
            if j.get("job_url"):
                st.link_button("Open posting", j["job_url"])

elif page == "Top Matches":
    st.subheader("Top Matches")
    for j in filtered:
        label = f"{j.get('attention_score', 0)} Attention · {j.get('fit_score', 0)} Fit · {j.get('job_title')} — {j.get('employer')}"
        with st.expander(label, expanded=j.get("attention_score", 0) >= 85):
            st.write(f"**Employer type:** {j.get('employer_type') or 'Not stated'}")
            st.write(f"**Location/work model:** {j.get('location') or 'Not stated'}")
            st.write(f"**Base pay:** {money(j.get('base_pay_min'))} – {money(j.get('base_pay_max'))}")
            st.write(f"**Connection established:** {j.get('connection_established') or 'No'}")
            st.write(f"**Connection name:** {j.get('connection_name') or 'None recorded'}")
            st.write(f"**Applied:** {j.get('applied') or 'No'}")
            st.write(f"**Benefits:** {j.get('benefits') or 'Not stated'}")
            st.write(f"**Posted / age:** {j.get('posted') or 'Not stated'}")
            st.write(f"**Closing date:** {j.get('closing_date') or 'Not stated'}")
            st.write(f"**Next action:** {j.get('next_action') or 'Not stated'}")
            st.caption(j.get("attention_factors") or "")
            if j.get("job_url"):
                st.link_button("Open posting", j["job_url"])

else:
    st.subheader("Pipeline")
    df = pd.DataFrame(filtered)
    ordered = [
        "attention_score", "fit_score", "job_title", "employer", "employer_type", "location",
        "base_pay_min", "base_pay_max", "connection_established", "connection_name", "applied",
        "status", "next_action", "benefits", "posted", "closing_date", "attention_factors", "job_url"
    ]
    visible = [c for c in ordered if c in df.columns]
    st.dataframe(df[visible], use_container_width=True, hide_index=True)
    st.info("Launchpad is the only source of truth. Update connection/application fields in Launchpad; use Refresh Launchpad here to pull the latest values.")
