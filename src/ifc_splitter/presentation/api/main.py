from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio
from rich.logging import RichHandler

from ifc_splitter.presentation.api.routes import router
from ifc_splitter.presentation.api.dependencies import get_job_manager

# Setup Logging similar to CLI
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)

async def run_periodic_cleanup():
    while True:
        try:
            # Run cleanup every 10 minutes, removing jobs older than 1 hour
            await asyncio.sleep(600) 
            job_manager = get_job_manager()
            job_manager.cleanup_old_jobs(max_compound_seconds=3600)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"Error during scheduled cleanup: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    cleanup_task = asyncio.create_task(run_periodic_cleanup())
    yield
    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="IFC File Splitter API",
    description="REST API for splitting and filtering IFC files.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS (Allow all for development, restrict for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")



@app.get("/health")
def health_check():
    return {"status": "ok"}
