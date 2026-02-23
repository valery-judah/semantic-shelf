from fastapi import FastAPI

from books_rec_api.api.routes.books import router as books_router
from books_rec_api.api.routes.recommendations import router as recommendations_router
from books_rec_api.api.routes.users import router as users_router
from books_rec_api.config import settings

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)
app.include_router(books_router)
app.include_router(recommendations_router)
app.include_router(users_router)
