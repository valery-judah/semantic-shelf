# Database Subsystem Details

This document outlines the architecture, tools, and conventions used for the database subsystem in `books-rec-api`. It serves as a reference for future refactoring and extending persistence to other modules.

## Technology Stack

- **Relational Database Engine**: PostgreSQL
- **ORM / Query Builder**: SQLAlchemy 2.0 (using synchronous API and 2.0-style statements)
- **Database Driver**: `psycopg` (v3)
- **Migrations**: Alembic

## Design Choices & Rationale

1. **Synchronous SQLAlchemy**: We use the synchronous `psycopg` driver with standard `def` API routes. Fast API handles standard `def` route endpoints by automatically running them in an internal threadpool. This avoids having to rewrite the entire application's service layer to `async/await` while achieving good throughput and minimizing the blast radius of DB introduction.
2. **Repository Pattern**: All database access is encapsulated inside repository classes (e.g., `UsersRepository`). The broader application (services and routes) does not interact with SQLAlchemy objects directly. This creates a clean boundary and easier testing.
3. **Pydantic vs. SQLAlchemy Models**: 
   - `src/books_rec_api/models.py` defines the underlying table structure (SQLAlchemy `Mapped` classes). 
   - Repositories are responsible for mapping between SQLAlchemy models and the domain's Pydantic schemas (`UserRead`, `DomainPreferences`, etc.) before returning data to the service layer.

## Project Structure

- `src/books_rec_api/database.py`: Instantiates the SQLAlchemy `Engine` and the `SessionLocal` factory using connection settings from `config.py`. Exposes the `Base` declarative class.
- `src/books_rec_api/models.py`: Contains all SQLAlchemy model definitions. When adding new tables, add the model here and ensure it inherits from `Base`.
- `src/books_rec_api/dependencies/users.py` (and similar modules): Exposes the `get_db_session` dependency which yields a transaction-scoped `Session` per request and properly closes it.
- `migrations/`: The Alembic configuration directory. `env.py` has been configured to import our app's settings and target metadata automatically.

## How to Work with the Database

### Adding New Models

1. Create or update a model class in `src/books_rec_api/models.py`.
2. Ensure you use SQLAlchemy 2.0 style type annotations (e.g., `Mapped[str] = mapped_column(String, primary_key=True)`).
3. Generate a new migration:
   ```bash
   uv run alembic revision --autogenerate -m "Add new model"
   ```
4. Review the generated script in `migrations/versions/` for correctness.
5. Apply the migration:
   ```bash
   uv run alembic upgrade head
   ```

### Repositories

When building a new repository (e.g., `BooksRepository`):
- The `__init__` method should accept an active `sqlalchemy.orm.Session`.
- Expose methods that return Pydantic domain models or primitive types.
- To insert/update data, rely on the `session` (e.g., `self.session.add(entity)`, `self.session.commit()`, `self.session.refresh(entity)`).
- Ensure dependency injection modules instantiate the repository correctly using FastAPI's `Depends(get_db_session)`.

## Testing

For unit and integration testing, the application avoids hitting a real PostgreSQL database, drastically speeding up the test suite. 

- **In-Memory SQLite**: `tests/conftest.py` overrides the database engine using an in-memory SQLite database (`sqlite:///:memory:`).
- **Thread Safety Configuration**: Because FastAPI's TestClient might execute route handlers in thread pools, the SQLite connection must use `check_same_thread=False` and `StaticPool` to ensure all threads share the exact same in-memory DB connection.
- **Fixture Strategy**: The `db_session` fixture yields an isolated session. Since it's an in-memory database bound to the `Engine` using `StaticPool`, data inserted during testing persists across the connection. Ensure your tests explicitly use or rollback transactions if isolation issues arise.
