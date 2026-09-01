import os
import glob
import json

import models
from database import db

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_fixtures(verbose=True):
    """Insert default "fixture" data from fixtures/data/*.json.

    Each JSON file has the shape:
        {"model": <ModelName>, "unique_by": <field>, "records": [ {...}, ... ]}

    Records are inserted idempotently: a record whose `unique_by` value already
    exists is skipped, so user-edited data is never overwritten. Files are
    processed in sorted filename order (numeric prefixes control cross-model
    ordering, e.g. users before teams). Returns the number of inserted rows.

    Must run inside a Flask application context.
    """
    inserted_total = 0

    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.json"))):
        name = os.path.basename(path)

        with open(path, encoding="utf-8") as fp:
            fixture = json.load(fp)

        model = getattr(models, fixture.get("model", ""), None)
        if model is None:
            print(f"[fixtures] {name}: unknown model '{fixture.get('model')}', skipped")
            continue

        unique_by = fixture.get("unique_by")
        inserted = 0

        for record in fixture.get("records", []):
            # Skip records that already exist (matched by their natural key).
            if unique_by and unique_by in record:
                if model.query.filter_by(**{unique_by: record[unique_by]}).first():
                    continue

            # Build through the model constructor so property setters run
            # (e.g. User.Password hashes the plain-text value).
            db.session.add(model(**record))
            inserted += 1

        if inserted:
            db.session.commit()
            # Realign the serial sequence after inserting explicit primary keys.
            if hasattr(model, "fix_sequence"):
                model.fix_sequence()

        inserted_total += inserted

        if verbose:
            print(f"[fixtures] {name}: +{inserted} {model.__name__}")

    return inserted_total


def register_cli(app):
    """Register the `flask seed` command that runs load_fixtures()."""

    @app.cli.command("seed")
    def seed():
        count = load_fixtures()
        print(f"[fixtures] done, {count} new record(s).")
