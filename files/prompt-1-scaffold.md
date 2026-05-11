# Prompt 1 — Project Scaffold

Set up a monorepo for a full-stack trip planning app with this exact structure:

```
spotter-eld/
├── README.md
├── .gitignore
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── runtime.txt          (python-3.12.3)
│   ├── Procfile             (web: gunicorn trip_planner.wsgi)
│   ├── build.sh             (Render build script)
│   ├── trip_planner/        (Django project — settings.py, urls.py, wsgi.py)
│   └── planner/             (Django app)
│       ├── __init__.py
│       ├── apps.py
│       ├── urls.py
│       ├── views.py
│       ├── serializers.py
│       ├── tests.py
│       └── services/
│           ├── __init__.py
│           ├── geocoding.py
│           ├── routing.py
│           └── hos.py
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── api.js
        ├── styles.css
        └── components/
            ├── TripForm.jsx
            ├── RouteMap.jsx
            ├── DailyLogSheet.jsx
            └── TripSummary.jsx
```

Backend `requirements.txt` should pin:
- Django==5.0.6
- djangorestframework==3.15.1
- django-cors-headers==4.3.1
- requests==2.32.3
- gunicorn==22.0.0
- whitenoise==6.7.0
- python-decouple==3.8

Django `settings.py` must:
- Read `SECRET_KEY` and `DEBUG` from environment (python-decouple)
- `ALLOWED_HOSTS = ['*']` for now (we'll tighten later)
- Include corsheaders middleware with `CORS_ALLOW_ALL_ORIGINS=True` for dev
- Use whitenoise for static files
- `INSTALLED_APPS` includes `rest_framework`, `corsheaders`, `planner`

Frontend `package.json` should use Vite + React 18, with `leaflet`, `react-leaflet`, `axios` as deps.

Add a top-level README with setup instructions for backend and frontend. Create `.gitignore` covering Python, Node, .env, venv, __pycache__, node_modules, dist, db.sqlite3.

Don't add any business logic yet — just scaffold and make sure `python manage.py check` passes and `npm install && npm run dev` works.
