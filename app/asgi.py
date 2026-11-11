"""Production ASGI entrypoint including the marketplace MVP."""
from .marketplace import router as marketplace_router  # Register models before create_all
from .operations import router as operations_router
from .main import app

app.include_router(marketplace_router)

app.include_router(operations_router)
