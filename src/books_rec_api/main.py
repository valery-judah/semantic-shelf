from fastapi import FastAPI

from books_rec_api.api.routes.recommendations import router as recommendations_router
from books_rec_api.config import settings

app = FastAPI(title=settings.app_name)
app.include_router(recommendations_router)
