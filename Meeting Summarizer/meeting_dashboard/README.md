# Meeting Dashboard

AI-powered Flask app to upload meeting transcripts, generate summaries and action items with Groq, and visualize progress with an interactive timeline.

## Features
- User auth (register/login) with Flask-Login
- Upload transcript file or paste text
- Groq AI agents:
  - Summarizer: concise meeting summary
  - Action agent: extract action items (assignee, due date, priority)
- Dashboard with recent meetings, action items, and a Plotly timeline
- Inline status updates for action items

## Tech Stack
- Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login
- Groq API (chat completions)
- SQLite (default) or any SQL database via `DATABASE_URL`
- Bootstrap 5, Plotly.js

## Setup
1. Python 3.10+ recommended.
2. Create and activate a virtualenv.
3. Install deps:
```bash
pip install -r requirements.txt
```
4. Environment variables (create `.env` or set in shell):
- `FLASK_ENV=development`
- `SECRET_KEY=change-me`
- `GROQ_API_KEY=your_groq_api_key`
- Optional: `DATABASE_URL=sqlite:///meeting_dashboard.db`
5. Initialize the DB:
```bash
# Windows PowerShell
$env:FLASK_APP="main.py"
flask db init
flask db migrate -m "init"
flask db upgrade
```
6. Run the app:
```bash
flask run
```
Open `http://127.0.0.1:5000`.

### Enable Recording/Transcription
- Install system `ffmpeg` and ensure it is on your PATH.
- Browser recording uses MediaRecorder (`audio/webm`). The server converts to wav and transcribes via faster-whisper.


## Required APIs
- Groq Chat Completions (server-side): used by agents to summarize/extract tasks.
  - Endpoint: `POST https://api.groq.com/openai/v1/chat/completions`
  - Auth: `Authorization: Bearer <GROQ_API_KEY>`
  - Model: default `llama3-8b-8192` (configurable in `config.py`)

- Internal app APIs:
  - `PUT /api/action_items/<id>/status`
    - Body: `{ "status": "pending|in_progress|completed|cancelled" }`
    - Updates a task’s status.
  - `GET /api/action_items/timeline`
    - Returns aggregated action-item data for the Plotly timeline chart.
  - `POST /api/meetings/recording`
    - FormData: `audio` (webm), `title`, `description`, `participants`, `meeting_link`
    - Creates a meeting from a browser recording, transcribes, summarizes, extracts tasks.
  - `POST /api/google/create_meet_link`
    - JSON: `{ "meeting_id": 123, "attendees": ["user@example.com"], "summary": "...", "description": "..." }`
    - Creates a Google Calendar event with a Meet link and saves it to the meeting.

## Visualization
- Timeline (Plotly) on Dashboard
  - Counts of action items grouped by due date
  - Data source: `GET /api/action_items/timeline`
  - Frontend code: `templates/dashboard.html` (`#timelineChart`)

## Groq Integration
- Wrapper: `agents/groq_client.py`
- `SummarizerAgent` → generates summary
- `ActionAgent` → extracts action items
- Configure via env vars or `config.py` (`GROQ_API_KEY`, `GROQ_MODEL`).

## Key Files
- `main.py`: app entry
- `app.py`: routes/controllers
- `models.py`: `User`, `Meeting`, `ActionItem`
- `utils/viz_utils.py`: timeline/stat helpers
- `templates/`: Jinja templates (Bootstrap + Plotly)
- `utils/google_calendar.py`: Google Calendar helper to create Meet events

## Glossary (plain English)
- Template block: a named section in Jinja opened with `{% block ... %}` and closed with `{% endblock %}`.
- Pagination: splitting long lists into pages to speed up load times.
- API endpoint: a URL your app exposes to receive/return data.
- Timeline chart: time-based chart showing counts over dates.
- Status: task state (`pending`, `in_progress`, `completed`, `cancelled`).
- Priority: task importance (`low`, `medium`, `high`).

## Troubleshooting
- Dashboard 500 due to template: ensure all `{% block %}` have matching `{% endblock %}`.
- `/api/action_items/timeline` KeyError: confirm `viz_utils.py` updates `by_priority` (top-level), not inside `summary`.
- Groq errors: verify `GROQ_API_KEY` is set and network egress allowed.
- Google Calendar: ensure `client_secret.json` is placed in project root (or set `GOOGLE_CLIENT_SECRETS`), then first call to create a Meet link will open a local browser consent flow and store `token.pickle`.

## Production
- Use Gunicorn or another WSGI server.
- Use Postgres/MySQL via `DATABASE_URL`.
- Set a strong `SECRET_KEY`; disable debug.
