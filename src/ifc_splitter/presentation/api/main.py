from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio
import os
from rich.logging import RichHandler

from ifc_splitter.presentation.api.routes import router
from ifc_splitter.presentation.api.dependencies import get_job_manager

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
    logger = logging.getLogger("ifc_splitter")
    logger.info("=" * 70)
    logger.info("FastAPI Application Starting...")
    logger.info(f"Process ID: {os.getpid()}")
    logger.info(f"CWD: {os.getcwd()}")
    logger.info(f"/data exists: {os.path.exists('/data')}")
    
    try:
        job_manager = get_job_manager()
        logger.info(f"JobManager initialized with {len(job_manager.jobs)} existing jobs")
    except Exception as e:
        logger.error(f"Failed to initialize JobManager: {e}", exc_info=True)
        logger.warning("Application will start but job management may not work correctly")
    
    logger.info("=" * 70)
    
    cleanup_task = asyncio.create_task(run_periodic_cleanup())
    yield
    # Shutdown
    logger.info("FastAPI Application Shutting Down...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="IFC File Splitter API",
    description="REST API for splitting and filtering IFC files.",
    version="1.0.0",
    lifespan=lifespan # https://fastapi.tiangolo.com/advanced/events/#lifespan
)

# https://render.com/articles/fastapi-production-deployment-best-practices
# TODO: configure allowed origins via env variable
origins_env = os.getenv("ALLOWED_ORIGINS", "*")
origins = [origin.strip() for origin in origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")



@app.get("/health")
def health_check():
    return {"status": "ok"}
