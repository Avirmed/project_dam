import os
from dotenv import load_dotenv

load_dotenv()

r"""
    .\python313\python.exe -m pip install Flask Flask-SQLAlchemy psycopg2 | schedule
    .\python313\python.exe -m pip install Flask-Migrate
    .\python313\python.exe -m pip install Flask-Login
    .\python313\python.exe -m pip install gevent
    .\python313\python.exe -m pip install dotenv
    .\python313\python.exe -m pip install schedule
    .\python313\python.exe -m pip install beautifulsoup4
    .\python313\python.exe -m pip install portalocker
    
    
    .\python313\python.exe -m pip install pipreqs
    .\python313\Scripts\pipreqs.exe . --encoding utf-8 --ignore pgsql,python313,static --force
    
    
    .\python313\python.exe -m pip install flasgger
    
    
    .\python313\python.exe -m pip install pre-commit
    .\python313\Scripts\pre-commit.exe install
    .\python313\Scripts\pre-commit.exe run --all-files
    
    .\python313\python.exe -m pip install black
    .\python313\Scripts\black.exe .
    
    .\python313\python.exe -m pip install flake8
    .\python313\Scripts\flake8.exe .
"""


class Config:
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{os.getenv('DB_USERNAME')}:"
        f"{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME')}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }

    SEND_FILE_MAX_AGE_DEFAULT = 31536000
