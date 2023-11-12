# Mini project for DW & DSS course

## Prerequisites

- `python` 3.10 & `pip` 22.0.2
- `docker` 24.0.7
- `docker-compose` 1.29.2

## Installation

1. Install python dependencies
   ```bash
   pip install -r requirements.txt
   ```
2. Start `ClickHouse` database
   ```bash
   docker-compose up -d
   ```
3. Install pre-commit hooks
   ```bash
   pre-commit install
   ```

All-in-one command:

```bash
pip install -r requirements.txt && docker-compose up -d && pre-commit install
```

## Start application

Run this command:

```bash
uvicorn main:app --reload
```

Swagger documentation will be available at <http://localhost:8000/docs> or <http://localhost:8000/redoc>.

## Play with `ClickHouse` database

```bash
docker exec -it olapdb clickhouse-client
```

See [ClickHouse documentation](https://clickhouse.com/docs/) for more details.
