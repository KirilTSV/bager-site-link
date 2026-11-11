"""Production ASGI entrypoint including the marketplace MVP."""
from .marketplace import router as marketplace_router  # Register models before create_all
from .main import app

app.include_router(marketplace_router)
