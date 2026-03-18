"""
Progress tracking service for long-running background tasks
Uses Redis for storing progress state
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import structlog
from services.cache import get_cache

logger = structlog.get_logger()


class ProgressTracker:
    """Track progress of long-running background tasks"""

    @staticmethod
    async def create_job(
        user_id: str,
        job_type: str,
        total_items: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new progress tracking job

        Args:
            user_id: User ID who initiated the job
            job_type: Type of job (e.g., 'force_refresh', 'bulk_refresh')
            total_items: Total number of items to process
            metadata: Additional job metadata

        Returns:
            job_id: Unique job identifier
        """
        job_id = str(uuid.uuid4())
        cache = get_cache()

        job_data = {
            "job_id": job_id,
            "user_id": user_id,
            "job_type": job_type,
            "status": "running",
            "total_items": total_items,
            "processed_items": 0,
            "failed_items": 0,
            "current_batch": 0,
            "total_batches": 0,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "message": "Starting...",
            "metadata": metadata or {}
        }

        # Store in Redis with 1 hour TTL
        if cache:
            await cache.set(
                f"job:{job_id}",
                job_data,
                ttl=3600  # 1 hour
            )

        logger.info(f"Created progress job",
                   job_id=job_id,
                   job_type=job_type,
                   user_id=user_id,
                   total_items=total_items)

        return job_id

    @staticmethod
    async def update_progress(
        job_id: str,
        processed_items: int,
        failed_items: int = 0,
        current_batch: int = 0,
        total_batches: int = 0,
        message: str = ""
    ):
        """Update job progress"""
        cache = get_cache()
        if not cache:
            return

        job_data = await cache.get(f"job:{job_id}")
        if not job_data:
            return

        job_data["processed_items"] = processed_items
        job_data["failed_items"] = failed_items
        job_data["current_batch"] = current_batch
        job_data["total_batches"] = total_batches
        if message:
            job_data["message"] = message

        await cache.set(f"job:{job_id}", job_data, ttl=3600)

    @staticmethod
    async def complete_job(
        job_id: str,
        success: bool = True,
        message: str = ""
    ):
        """Mark job as completed"""
        cache = get_cache()
        if not cache:
            return

        job_data = await cache.get(f"job:{job_id}")
        if not job_data:
            return

        job_data["status"] = "completed" if success else "failed"
        job_data["completed_at"] = datetime.utcnow().isoformat()
        if message:
            job_data["message"] = message

        await cache.set(f"job:{job_id}", job_data, ttl=3600)

        logger.info(f"Completed progress job",
                   job_id=job_id,
                   success=success,
                   message=message)

    @staticmethod
    async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
        """Get current job status"""
        cache = get_cache()
        if not cache:
            # Return a default running status if cache is unavailable
            # This prevents frontend errors when Redis is down
            return {
                "job_id": job_id,
                "status": "running",
                "total_items": 1000,
                "processed_items": 0,
                "failed_items": 0,
                "progress_percent": 0,
                "message": "Processing... (cache unavailable)"
            }

        try:
            job_data = await cache.get(f"job:{job_id}")
            if not job_data:
                return None

            # Calculate percentage
            total = job_data.get("total_items", 0)
            processed = job_data.get("processed_items", 0)
            failed = job_data.get("failed_items", 0)

            if total > 0:
                job_data["progress_percent"] = round(((processed + failed) / total) * 100, 1)
            else:
                job_data["progress_percent"] = 0

            return job_data
        except Exception as e:
            logger.error("Failed to get job status", job_id=job_id, error=str(e))
            return None

    @staticmethod
    async def get_user_jobs(user_id: str, job_type: Optional[str] = None) -> list:
        """Get all jobs for a user"""
        cache = get_cache()
        if not cache:
            return []

        # Note: This is a simplified implementation
        # In production, you might want to use Redis SCAN or a separate index
        return []
