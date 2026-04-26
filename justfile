lint:
    ruff check . --fix
    ruff format .

run:
    uvicorn src.main:app --reload --port 8765