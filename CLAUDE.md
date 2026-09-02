# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ Ground rule — always confirm before touching files

**Always ask the user for confirmation before creating a new file or editing an existing file.** State what you intend to change and wait for an explicit go-ahead first — do not create or modify files proactively, even for changes that look trivial. Reading, searching, and analyzing the codebase need no confirmation.

## What this is

A Flask + PostgreSQL dashboard for managing water/dam monitoring data (projects, river basins, stations, sensors, cameras, samplings, areas, teams, users). Server-rendered Jinja templates driven by a jQuery/Tabulator frontend. UI strings and many code comments are in Mongolian/Thai; the maintainer communicates in Mongolian.

## Bundled toolchain (Windows)

The repo vendors its own interpreter and database — **use them, don't assume a system install**:

- Python: `python313\python.exe` (all commands below assume this)
- PostgreSQL server: `pgsql\` (bundled, runs on port **5444**)
- **Never modify** `pgsql\`, `python313\`, or `static\js\libs\` (vendored third-party). Do JS work in `static\js\` (not `libs`).

## Commands

- **Run the app:** `app_run.bat` (or `python313\python.exe app.py`). Serves on port 88 (gevent `WSGIServer` in prod; Flask dev server with reloader when `APP_DEBUG=True`).
- **Start/stop DB:** `pgsql_start.bat` / `pgsql_stop.bat`.
- **Migrate DB:** `migrate_db.bat` runs `flask db migrate` + `flask db upgrade` in one shot (auto-inits `migrations/` if missing). Manual: set `FLASK_APP=app.py`, then `python313\python.exe -m flask db migrate -m "..."` and `... db upgrade`.
- **Format + lint:** `pre-commit.bat` runs Black then Flake8, both excluding `pgsql,python313,dist`; Flake8 uses `--max-line-length=150 --extend-ignore=E203`. Match these when writing code.
- **Regenerate package imports:** after adding/removing a file in `models/` or `routes/`, run `generate_init.bat` (`generate_init.py`). It rewrites each `__init__.py` with `__all__` and the imports (`from .<m> import *` for models, `from .<m> import <m>_bp` for routes). Editing those `__init__.py` files by hand will be overwritten.
- **Load default data (fixtures):** `load_fixtures.bat` (or `flask seed`) runs `fixtures/loader.py::load_fixtures()`, which reads `fixtures/data/*.json` and inserts them **idempotently** (skips rows that already exist by their natural key, so user edits are never overwritten). This also runs automatically at app startup (`run_startup_checks`). To add seed data, drop a `NN_<name>.json` file in `fixtures/data/` — format `{"model": <ModelName>, "unique_by": <field>, "records": [...]}`; the numeric prefix controls load order. Records are built via the model constructor, so property setters run (e.g. `User.Password` is hashed). This replaced the old per-model `create_default_*` seeders.
- **No test suite exists.** There is no build step (static assets are committed).

Config comes from a `.env` file (see `README.md`): `DB_USERNAME/PASSWORD/HOST/PORT/NAME`, `APP_SECRET_KEY`, `APP_DEBUG`. `config.py` builds `SQLALCHEMY_DATABASE_URI` from those.

## Architecture

### App wiring
`app.py` → `create_app()` is the factory: applies `ProxyFix`, loads `config.Config`, installs a `CustomJSONProvider` (dates → strings, `ensure_ascii=False`), then `db.init_app`, `Migrate`, JWT, Flask-Login, `register_handlers`, `register_blueprints`. `run_startup_checks` verifies the DB connection and seeds a default `User` and `Settings` before serving. `db` is a bare `SQLAlchemy()` in `database.py` (import from there, not from a Flask extension object). **Keep `app.py` minimal** — it only wires components together and starts the server; setup and helper logic (logging, login manager, JSON provider, the startup banner, etc.) lives in `extensions.py` (or the relevant module), never inlined in `app.py`.

### The "module" convention (most important pattern)
Each feature is a **module** name (`stations`, `sensors`, `cameras`, `samplings`, `areas`, `teams`, `users`, `projects`, `riverbasins`) wired in **four parallel places**:

| Layer | Location |
|-------|----------|
| Model | `models/<module singular>.py` |
| API routes | `routes/<module singular>.py` → blueprint `<name>_bp`, mounted at `/api/<module>` in `urls.py` |
| Templates | `templates/dashboard/<module>/` — `index.html` (Tabulator list) + `form.html` + `form-<tab>.html` |
| Frontend JS | `static/js/dashboard/<module>.js` |

`urls.py::register_blueprints` maps blueprints to `/api/<module>` prefixes. `templates/dashboard/index.html` dynamically includes `dashboard/<Module>/index.html` and loads `static/js/dashboard/<Module>.js` from the `Module` route param. Adding a module = create all four, add it to the `api_list` in `urls.py`, then run `generate_init.py`.

**Shared/common dashboard templates go in `templates/dashboard/main/`.** Any page or partial that is used across modules or generically (shared macros, reusable form snippets, common includes) belongs there — not inside a specific module's folder. Reference them as `dashboard/main/<file>.html` (e.g. `{% from "dashboard/main/config_field.html" import render_field with context %}`).

**Reviewing or changing a module means checking its whole file set, not a single file.** When asked to look at / fix / improve a module — e.g. "check `user.py`" or "the users module" — always review all of the module's parallel files together, because a change in one usually implies changes in the others:
- `models/<module>.py`
- `routes/<module>.py`
- `urls.py` (blueprint registration + page routing)
- `static/js/dashboard/<module>.js` **or** `static/js/modules/<module>.js`
- `templates/dashboard/<module>/*` **or** `templates/modules/<module>/*`

The `dashboard` vs `modules` split is the admin dashboard vs the public/front site; a module may have files under either or both.

### Model conventions
Models subclass `db.Model` and expose **classmethods that hold the business logic** — `save(params)`, `delete(params)`, `list(params)`, `getData(id)`, plus an instance `serialize()`. Class-level `sort`, `searchFields`, `required_fields` drive generic list/search/validation. `save()` handles both insert and update by iterating `__table__.columns` generically; JSONB columns are detected and JSON-parsed via `_parse_json_fields`. `list()` returns `{data, sort, last_row, last_page, filtered}` plus Tabulator column defs assembled in the route. Routes stay thin: merge `request.args`/JSON/form into one dict and delegate to the model classmethod, returning `jsonify(result), result["Code"]`.

### Frontend conventions
`static/js/project.js` holds the **generic** form engine shared by every module: `updateEditForm` (populates a form from a serialized record, including `.app-json-data[data-field]` JSONB blocks), `serializeEditForm`, and `initTabulators`. Per-module JS files (e.g. `stations.js`) open a Bootbox dialog with the cloned `.form-tmp`, wire `ajaxForm` to `/api/<module>/save`, and in `beforeSerialize` collect `.app-json-data` blocks into JSON payloads. A global `LOCAL_VARIABLES` carries `Authorization` (incl. `UserType`) and `StaticText`; `pagePermission` arrays gate pages by `UserType`.

### `util/statictext.py` — single source of truth for ALL text (critical rule)
**Never hard-code user-facing text — labels, messages, button captions, dropdown options, icons, field titles, response messages — anywhere in Python, Jinja templates, or JavaScript. Always add it to `util/statictext.py` and reference it from there.** This is a core convention of the project; string literals scattered in code/markup are treated as a mistake to fix.

What lives here: per-model field labels (`<Model>Field`), form tab definitions (`<Model>FormTab`), nested form schemas (`StationConfigures`, `WaterConfigures`, `APIConfigures`, `FTPConfigures`, `Sensor*Configures`, `AreaConfigures`, …), dropdown option maps (`Regions`, `UserTypes`, `SensorTypes`, `API_Protocols`, …), `Messages`, `ResponseCode`, `Icon` (HTML icon snippets), `StatusLabel`, `Export`, `Images`, and app constants (`APP_NAME`, `APP_COLOR`, …). Reuse existing keys by cross-referencing (e.g. `CameraFormTab` reuses `CameraField["CameraConfigures"]`) rather than repeating a literal.

How each layer consumes it:
- **Backend (Python):** `from util import statictext`, then `statictext.Messages["SuccessSaved"]`, `statictext.ResponseCode[code]`, `statictext.StationField["SiteCode"]`, etc. Routes/models return these, never inline English/Thai strings.
- **Templates (Jinja):** the value is passed in as `StaticText=statictext` and used as `StaticText.Icon.Save | safe`, `StaticText.StationFormTab`, `StaticText.Save`, etc. Templates loop over these dicts to render forms, so adding a field/tab/config is an edit here, not new HTML.
- **Frontend (JS):** `routes/main.py::/init` reflects the whole `statictext` module to JSON (`vars(statictext)` minus a few filesystem-path keys in `excluded_keys`). `static/js/project.js` fetches `/main/init` once into `LOCAL_VARIABLES.StaticText` and caches it in `localStorage` (key = the `app` attribute). JS reads strings as `LOCAL_VARIABLES.StaticText.Messages.LettersOnly`, `LOCAL_VARIABLES.StaticText.Icon['-']`, `LOCAL_VARIABLES.StaticText.RequiredField`, `LOCAL_VARIABLES.StaticText.UserTypes[type]`, etc.

Consequences to remember: (1) everything in `statictext.py` except the `excluded_keys` paths is shipped to the browser and cached client-side — **never put secrets, tokens, or absolute filesystem paths there**; add non-public constants elsewhere or to `excluded_keys`. (2) Because `LOCAL_VARIABLES.StaticText` is cached in `localStorage`, a newly added string may not appear until the cached copy is refreshed (the `/init` fetch on load / clearing storage) — expect that when a new key "doesn't show up."

### Auth
Flask-Login sessions (`login_view = /dashboard/login`) plus a JWT manager. Access is gated by `UserType`: routes filter data for `UserType in [3, 4]` via `Team.get_user_teams`, and the frontend gates pages with `pagePermission`.

### Background worker & services (`services/`)
`app.py` starts one daemon thread (`services/scheduler.py::start_worker`) right after the startup checks (only in the reloader child in debug). It ticks every 5 s, runs each registered job inside its own app context / DB session, and swallows job errors so the web server is never affected. `WORKER_ENABLED` (Settings) switches it off. Jobs:
- `http_sender` — delivers `HttpLog` rows with Status 0 (Queue). Rows are queued by `StationData.ingest` → `HttpLog.enqueue_for_station` the moment a device posts data (design: "when new data hits our DB"); payload built by `util.build_http_payload` from the HTTP service's Parameter Mapping; GET → query string, POST/PUT → JSON or `key=value` body; retries per `RetryAttempts`/`RetryDelay`; full URL, request, response code/body kept on the row (Status 1 Sent / 2 Failed, `HttpLogStatuses`).
- `csv_logger` — every `LogInterval` minutes (clock-aligned) appends a row to `tmp/csv/<logger>/<FilenameFormat>` and uploads it via the logger's File Transfer (`services/file_transfer.py`, stdlib `ftplib`, FTP/FTPS explicit+implicit, directory structure); outcome in `CsvLogger.LastRun/LastResult`.
- `event_watcher` — Security cameras drop `<IP>_<ch>_<yyyymmddHHMMSS>_<EVENT>.jpg` into `Camera.eventWatchPath` (`tmp/security_in`); files become `EventLog` rows (camera matched by RSTP/Onvif IP), images move to `EventLog.drfFilePath` (`static/data/events/<yyyymm>/`, served from `EventLog.filePath`), unparseable files to `_unmatched/`. Public page `/events` (templates/modules/events, static/js/modules/events.js) with approve/reject.
- `image_uploader` — files under `Camera.imageOutPath/<CameraID>/` (`tmp/images_out`) are sent through the camera's Upload JPG (FTP) settings; delivered files move to `sent/`; outcome in `Camera.LastUploadRun/LastUploadResult`. Folder paths are class attributes (like `Station.drfFilePath`), not Settings rows.

Related modules/endpoints: `POST /api/inbound/<DeviceID>` (device-facing REST API server, gated by `Station.Meta["API"]`: status, source allow-list, Basic/Bearer/API-Key auth, Inbound Data Mapping → `StationData` with `Data` mapped + `Raw`), `/api/stationdata` (read-only), `/api/httplog` (list/counters/get), `/api/eventlog` (list/counters/get/action). Public map status (`/api/stations/sites`) comes from the newest `StationData` per station vs the StationConfigures thresholds; older than `DATA_TIMEOUT_MINUTES` → "No connection". TLS certificate uploads for the REST API tab live in `certs/<StationID>/` (git-ignored, never web-served). Settings rows seeded by fixtures: `DATA_TIMEOUT_MINUTES`, `WORKER_ENABLED` (shown as a switch; `statictext.BooleanSettings`).

Config-field extras understood by `templates/dashboard/main/config_field.html` + `project.js`: `type` file / generate / checkbox, `show_when` (conditional visibility, AND of listed fields), `help`, table `column_options` (select column). Camera RTSP/ISAPI links are generated by `Camera.build_links()` (and previewed by `renderCameraLinks` in `cameras.js`).

## Working style (from the former Copilot rules)
- **Write all code comments in English.** Even though some existing comments (and all UI text via `statictext.py`) are in Mongolian/Thai, every new or edited source comment — in Python, JS, Jinja, and batch files — must be in English.
- Read the existing files for a module before changing it; mirror the established pattern and naming.
- Prefer small, targeted edits over rewrites; avoid adding dependencies.
- When a change touches routes + models + templates + DB together, note the cross-layer impact before editing.
