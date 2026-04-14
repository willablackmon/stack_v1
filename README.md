# Stack Web App for Render

This package is the Render-ready web app version of the updated `stack-v0.1.ipynb` notebook.

## What is included

- Flask app packaged under `stack_webapp/`
- `render.yaml` Blueprint for one Render web service
- `requirements.txt` for Render's standard Python build flow
- `.env.example` for local development only
- `.gitignore` that keeps `.env` out of Git
- `wsgi.py` entrypoint for Render / Gunicorn

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
    │   ├── css/stack.css
    │   └── js/app.js
    ├── templates/index.html
    └── utils/
        ├── __init__.py
        ├── data_providers.py
        ├── hubspot_client.py
        └── table_helpers.py
```

## Local development

```bash
pip install -r requirements.txt
pip install -e .
cp .env.example .env
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
- `DEBUG_USERID` = `true` or `false`
- `PYTHON_VERSION` = `3.11.11`
