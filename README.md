# Career Command Center

Streamlit dashboard for the My Career project.

## Source of truth

The dashboard reads job-tracking data directly from the native Google Sheet **Chakori → Company Tracker**.

Current tracked fields include:
- Fit Score
- Base Pay Min / Max
- Attention Score
- Connection Established?
- Connection Name
- Applied?
- Benefits
- Job URL
- Posted / Age
- Closing Date
- Attention Factors
- Employer Type

Attention Score combines technical fit, private-sector priority, remote/Augusta preference, compensation, connection status, application status, and urgency.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, fill in the Google service-account values, and share the Chakori spreadsheet with the service-account email as Viewer.

Do not commit `.streamlit/secrets.toml`.
