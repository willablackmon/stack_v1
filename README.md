# Stack Web App for Render

This version is prepared specifically for a GitHub -> Render deployment.

## What is included

- Flask app packaged under `stack_webapp/`
- `render.yaml` Blueprint for one Render web service
- `requirements.txt` for Render's standard Python build flow
- `.python-version` plus `PYTHON_VERSION` in `render.yaml` to pin Python
- `.env.example` for local development only
- `.gitignore` that keeps `.env` out of Git

## Project layout

```text
stack_webapp_render/
├── .env.example
├── .gitignore
├── .python-version
├── MANIFEST.in
├── README.md
├── pyproject.toml
├── render.yaml
├── requirements.txt
└── stack_webapp/
    ├── __init__.py
    ├── __main__.py
    ├── app.py
    ├── config.py
    ├── wsgi.py
    ├── static/
    ├── templates/
    └── utils/
```

## Local development

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
pip install -e .
```

3. Copy `.env.example` to `.env` and add your real HubSpot token.
4. Run locally:

```bash
python -m stack_webapp
```

Open `http://127.0.0.1:8000`.

## GitHub -> Render deploy

### Option 1: using `render.yaml`

1. Create a new GitHub repo and push this project.
2. In Render, choose **New > Blueprint**.
3. Connect the GitHub repo.
4. During setup, Render will prompt for `HS_TOKEN` because it is marked with `sync: false` in `render.yaml`.
5. Deploy.

### Option 2: create the web service manually

Use these settings:

- **Runtime:** Python
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn --bind 0.0.0.0:$PORT stack_webapp.wsgi:app`
- **Health Check Path:** `/health`

Add these environment variables in Render:

- `HS_TOKEN` = your HubSpot private app token
- `FLASK_SECRET_KEY` = a random secret string
- `APP_TITLE` = `Stack` (optional)
- `PYTHON_VERSION` = `3.11.11`

## Security notes

- Do **not** commit a real `.env` file.
- For Render, keep secrets in the Render dashboard or let the Blueprint prompt you for them.
- `Opp Insights` and `Opp Search` are still placeholders, matching the current notebook conversion.

## Entrypoint used by Render

```bash
gunicorn --bind 0.0.0.0:$PORT stack_webapp.wsgi:app
```
