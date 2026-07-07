# Project DAM

This project runs a web application using Flask.

## Required Software

- Download PostgreSQL and the Python source: https://drive.google.com/file/d/1B-51yfms0YcM3Hi4IpTOz6C8wYWc0Zho/view
- Python 3.13 (in this project, Python may be located in the `python313\python.exe` folder)
- PostgreSQL (in this project, the server files are inside `pgsql\`)
- The libraries listed in `requirements.txt`

## Project Files

- `app.py` — Flask application entry point
- `.env_example` — example environment variables
- `pgsql_start.bat` — start the PostgreSQL server
- `pgsql_stop.bat` — stop the PostgreSQL server
- `migrate_db.bat` — run database migrations
- `app_run.bat` — run the application

## Configuration

1. Copy the `.env_example` file to `.env`.
2. Open the `.env` file and set the following values:

```ini
APP_DEBUG=False
APP_SECRET_KEY=...

DB_USERNAME=postgres
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5444
DB_NAME=smart_guide_db
```

- If you use the PostgreSQL server inside `pgsql\`, keep `DB_PORT=5444`.
- If you use a different server, configure the `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, and `DB_NAME` values accordingly.

## Installing the Required Python Libraries

If the project contains `python313\python.exe`, use the following command:

```bat
python313\python.exe -m pip install -r requirements.txt
```

If Python is in your PATH:

```bat
python -m pip install -r requirements.txt
```

## Starting the PostgreSQL Server

1. Run the `pgsql_start.bat` file.
2. Verify that the server started successfully.
3. Make sure the `DB_HOST`, `DB_PORT`, and `DB_NAME` values in the application are correctly written in `.env`.

## Stopping the PostgreSQL Server

```bat
pgsql_stop.bat
```

## Database Migrations

While the PostgreSQL server is running, execute the following command:

```bat
migrate_db.bat
```

This applies the migrations in the `migrations/` folder and updates the database.

## Running the Application

### 1. Use `app_run.bat`

```bat
app_run.bat
```

### 2. Run `app.py` directly

```bat
python313\python.exe app.py
```

If `APP_DEBUG=True` is set, the server runs in debug mode.

## Development Tips

- If the server does not start, check `pgsql_start.bat` and the `DB_` values in `.env`.
- `APP_PORT` is not read from `.env` in `config.py`, so port 88 is used in `app.py`.
- Using `Flask-Migrate` allows you to update the database schema.

## Help

- If the application does not run, first check whether PostgreSQL is running, whether the paths in `.env` are correct, and whether the libraries in `requirements.txt` are installed.
- The `run_startup_checks` section in `app.py` will stop execution if it cannot connect to PostgreSQL.
