"""
Background Worker - arq Worker Settings

Defines background job configurations and worker entry point.
Jobs run asynchronously, outside of request/response flow.
"""

from arq import cron
from arq.connections import RedisSettings

from app.config import get_settings
from app.tasks.sync_tasks import sync_user_classroom, sync_all_active_users
from app.tasks.embedding_tasks import generate_embeddings_for_course
from app.tasks.reminder_tasks import schedule_reminders, send_pending_reminders

settings = get_settings()


async def startup(ctx: dict) -> None:
    """Initialize worker dependencies on startup."""
    from app.models.database import init_db
    from app.integrations.vector_store import init_vector_store
    from app.utils.logging import setup_logging, get_logger
    
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Starting background worker")
    
    await init_db()
    await init_vector_store()
    
    ctx["logger"] = logger


async def shutdown(ctx: dict) -> None:
    """Cleanup on worker shutdown."""
    from app.models.database import close_db
    await close_db()
    ctx["logger"].info("Worker shutdown complete")


class WorkerSettings:
    """arq worker configuration."""
    
    # Redis connection
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    
    # Available job functions
    functions = [
        sync_user_classroom,
        sync_all_active_users,
        generate_embeddings_for_course,
        schedule_reminders,
        send_pending_reminders,
    ]
    
    # Cron jobs (periodic tasks)
    cron_jobs = [
        # Sync active users every 15 minutes
        cron(sync_all_active_users, minute={0, 15, 30, 45}),
        # Schedule reminders every hour
        cron(schedule_reminders, minute=0),
        # Send pending reminders every 5 minutes
        cron(send_pending_reminders, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    ]
    
    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown
    
    # Worker settings
    max_jobs = 10
    job_timeout = 300  # 5 minutes max per job
    keep_result = 3600  # Keep results for 1 hour
