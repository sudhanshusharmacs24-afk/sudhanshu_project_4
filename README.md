# 🎓 AcademiaCRM — AI-Powered B2B Academia Sales CRM

A full-featured CRM system built with Python + Flask for managing college/university outreach and partnership lifecycles.

---

## 🚀 Features

| Module | Description |
|--------|-------------|
| **Lead Management** | Capture institution name, location, contact, programs, lead source & status |
| **Sales Pipeline** | 6-stage pipeline: New Lead → Contacted → Meeting → Proposal → Negotiation → Closed |
| **AI Lead Scoring** | Automatic priority scoring (0–100) based on student strength, institution type, programs, source |
| **AI Next Best Action** | Context-aware recommendations for each lead stage |
| **AI Outreach Messages** | Personalized email drafts generated per institution |
| **AI Follow-up Suggestions** | Urgency-tagged actionable suggestions |
| **Follow-Up Tasks** | Create, track, and complete tasks with due dates and overdue alerts |
| **Activity Log** | Full audit trail of all actions per institution |
| **Dashboard** | Real-time stats, pipeline chart, lead source chart, activity feed |
| **REST API** | JSON endpoints for status updates and AI analysis |

---

## 📦 Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

```bash
# 1. Navigate to project folder
cd crm

# 2. Create virtual environment (recommended)
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python app.py
```

### Access
Open your browser at: **http://localhost:5000**

The app auto-creates the database and seeds 6 sample institution leads on first run.

---

## 🗂️ Project Structure

```
crm/
├── app.py                  # Main Flask application + AI engine
├── requirements.txt        # Python dependencies
├── README.md
├── instance/
│   └── crm.db              # SQLite database (auto-created)
└── templates/
    ├── base.html           # Sidebar layout + global styles
    ├── dashboard.html      # Stats, charts, pipeline
    ├── leads.html          # Lead list with filters
    ├── lead_detail.html    # Full lead view + AI panel
    ├── add_lead.html       # Add new lead form
    ├── edit_lead.html      # Edit existing lead
    └── followups.html      # Follow-up task tracker
```

---

## 🧠 AI Intelligence Engine

The AI engine (built-in, no external API key needed) scores each lead on:

| Factor | Max Points |
|--------|-----------|
| Student Strength (10K+ = 35pts) | 35 |
| Institution Type (IIT/NIT = 30pts) | 30 |
| Programs of Interest (5pts each) | 20 |
| Lead Source (Referral = 15pts) | 15 |

**Priority Labels:**
- 🔴 High Priority: Score ≥ 70
- 🟡 Medium Priority: Score 40–69
- 🟢 Low Priority: Score < 40

---

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/leads` | GET | Get all leads as JSON |
| `/api/ai/analyze/<id>` | GET | Re-run AI analysis on a lead |
| `/api/leads/status_update` | POST | Update lead status |
| `/api/dashboard/stats` | GET | Get pipeline stats |

---

## 📸 Pages

- `/` — Dashboard with charts and stats
- `/leads` — All institutions with search/filter
- `/leads/add` — Add new institution lead
- `/leads/<id>` — Lead detail with AI intelligence panel
- `/leads/<id>/edit` — Edit lead details
- `/followups` — Follow-up task center with overdue alerts

---

## 🛠️ Tech Stack

- **Backend:** Python 3, Flask, Flask-SQLAlchemy
- **Database:** SQLite (zero-config, file-based)
- **Frontend:** Jinja2 templates, vanilla CSS, Chart.js
- **AI Engine:** Custom rule-based scoring (no external API)
- **Icons:** Font Awesome 6

---

*Built for B2B Academia Sales Teams | v1.0*
