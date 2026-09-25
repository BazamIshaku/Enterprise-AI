# Enterprise AI

## Local development with Docker

The development stack includes Next.js, FastAPI, and PostgreSQL 16.

1. Copy `.env.example` to `.env` and replace `JWT_SECRET` with a long random value.
2. Start the stack:

   ```sh
   docker compose up --build -d
   ```

3. Open `http://localhost:3000`.

The API is available at `http://localhost:8000`, and PostgreSQL is exposed to
the host on port `5433` to avoid conflicts with an existing local database.
Alembic migrations run automatically when the backend starts. Source folders
are mounted into the containers for local development.

Stop the stack without deleting database data:

```sh
docker compose down
```
