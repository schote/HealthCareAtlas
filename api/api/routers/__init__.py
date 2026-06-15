from .hospitals import router as hospitals_router
from .regions import router as regions_router
from .metrics import router as metrics_router
from .deficit import router as deficit_router

__all__ = ["hospitals_router", "regions_router", "metrics_router", "deficit_router"]
