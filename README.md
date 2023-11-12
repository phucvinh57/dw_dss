# Mini project for DW & DSS course

## Project description

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

To play with `ClickHouse` database you can use `clickhouse-client`:

```bash
docker exec -it olapdb clickhouse-client
```

# Start application

Run this command:

```bash
uvicorn main:app --reload
```

Swagger documentation will be available at <http://localhost:8000/docs> or <http://localhost:8000/redoc>.
