# CLAUDE.md

Ferrule: a Django app for tracking tool rentals.

## Commands
- Run: `uv run manage.py runserver`
- Test: `uv run pytest`

## Layout
- `rentals/` holds models and views; `templates/` holds HTML.
- Dependencies: Django, psycopg, pytest-django.

## Rules
- Use class-based views.
- Migrations go in their own commit.
