from .settings import *  # noqa: F403,F401

# Use SQLite for local test runs independent of Docker/PostgreSQL state.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",  # noqa: F405
    }
}
