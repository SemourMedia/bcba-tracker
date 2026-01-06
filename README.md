# 📊 BACB Fieldwork Tracker

> **Zero-cost, audit-proof fieldwork tracking for BCBA candidates.**  
> You own your data. We provide the logic.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **📈 Compliance Dashboard** | Real-time tracking of supervision ratios, monthly hours, and BACB requirements |
| **🛡️ Audit Defense** | Automatic detection of "red flags" (overlapping sessions, >12hr entries) that block saves |
| **📄 PDF Generation** | One-click generation of official BACB Monthly Verification Forms |
| **🔄 Smart Defaults** | Context-aware input that learns your schedule and reduces data entry friction |
| **📊 Burnout Tracker** | Optional "Energy Level" logging with heatmap visualization (never exported to official forms) |
| **📥 Legacy Import** | Import existing data from Ripley CSV exports |
| **🔐 Privacy-First** | Zero PII/PHI storage. Your data lives in YOUR Google Sheet. |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Cloud (Free)                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                      app.py                           │  │
│  │  • UI/UX (French Clinical Theme)                      │  │
│  │  • Compliance Engine                                  │  │
│  │  • PDF Generator                                      │  │
│  │  • Audit Validator                                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                │
│                   Google OAuth 2.0                          │
│                            │                                │
└────────────────────────────┼────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              Your Personal Google Sheet (Free)              │
│  ┌─────────────────────┐  ┌─────────────────────────────┐   │
│  │    Logs Tab         │  │    Config Tab               │   │
│  │  • Session entries  │  │  • Supervisors              │   │
│  │  • Timestamps       │  │  • Ruleset version          │   │
│  │  • Supervision type │  │  • Work hours/days          │   │
│  └─────────────────────┘  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Core Philosophy:** *"Bring Your Own Data."*  
- **App** = Stateless logic engine (this repo)
- **Database** = Your personal Google Sheet (you own it)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- A Google Cloud Project with OAuth 2.0 Credentials ([setup guide](docs/setup/google_oauth_setup.md))
- A Google Cloud Service Account for backend operations

### Local Development

```bash
# Clone the repo
git clone https://github.com/yourusername/bcba-tracker.git
cd bcba-tracker

# Install dependencies
pip install -r requirements.txt

# Configure secrets
cp .streamlit/secrets.example.toml .streamlit/secrets.toml
# Edit secrets.toml with your credentials

# Run the app
streamlit run app.py
```

### Deploy to Streamlit Cloud

See the full [Deployment Guide](docs/DEPLOYMENT.md).

---

## 📁 Project Structure

```
bcba-tracker/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── BACB_Monthly_Verification_Form.pdf  # Official form template
│
├── auth/
│   ├── google_oauth.py             # Google OAuth 2.0 flow
│   └── __init__.py
│
├── utils/
│   ├── calculations.py             # Compliance engine & math
│   ├── auditor.py                  # Audit "red flag" detector
│   ├── user_registry.py            # User management & lookup
│   ├── config_manager.py           # Settings persistence
│   ├── data_manager.py             # Google Sheets integration
│   ├── importer.py                 # Legacy data import (Ripley)
│   ├── pdf_maker.py                # PDF form filler
│   └── schema.py                   # Data validation schemas
│
├── data/
│   └── bacb_requirements.json      # Versioned BACB compliance rules
│
├── docs/
│   ├── DEPLOYMENT.md               # Cloud deployment guide
│   └── setup/
│       └── google_sheets_setup.md  # Sheet configuration
│
└── .streamlit/
    └── config.toml                 # Streamlit theme (Light Mode enforced)
```

---

## 📋 BACB Compliance Rules

The app supports **versioned rulesets** to handle changes in BACB requirements:

| Version | Supervision Ratio | Monthly Min | Monthly Max | Notes |
|---------|-------------------|-------------|-------------|-------|
| 2022    | 5% (Standard)     | 20 hrs      | 130 hrs     | Current standard |
| 2027    | 5% (Standard)     | 20 hrs      | 160 hrs     | Projected (editable) |

Rules are stored in `data/bacb_requirements.json` and can be updated without code changes.

---

## 🎨 Design System: "French Clinical"

| Element | Specification |
|---------|--------------|
| **Theme** | Light Mode Only |
| **Canvas** | Clinical White `#FFFFFF` |
| **Ink** | Vantablack `#000000` |
| **Accent** | Oxblood `#800000` |
| **Headers** | Playfair Display (Serif, Bold) |
| **Body** | Inter (Sans-serif) |
| **Data** | JetBrains Mono (Monospace) |
| **Corners** | Sharp (`border-radius: 0px`) |

---

## 🔒 Security Model

1. **App Access**: Google OAuth 2.0 (Sign in with Google)
2. **Data Access**: User-isolated Google Sheets (managed via Registry)
3. **User Role**: Self-service onboarding (User creates sheet, app links it)
4. **Privacy**: No PII/PHI columns. Sessions linked to Supervisor + Activity, never patients.

---

## 🧪 Development

```bash
# Run tests
pytest tests/

# Generate mock data
python scripts/generate_mock_data.py
```

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [Streamlit](https://streamlit.io/) for the incredible framework
- [BACB](https://www.bacb.com/) for clear certification standards
- The behavior analysis community for feedback and testing

---

<p align="center">
  <strong>Built with ❤️ for BCBA candidates everywhere.</strong>
</p>