"""
File management utilities for the video generator.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FileManager:
    """
    Manages file operations for the video generator.

    Features:
    - Temporary file cleanup
    - Output file management
    - Storage quota management
    """

    def __init__(
        self,
        base_path: str = "storage",
        temp_dir: str = "temp",
        output_dir: str = "outputs",
        cache_dir: str = "cache"
    ):
        self.base_path = Path(base_path)
        self.temp_dir = self.base_path / temp_dir
        self.output_dir = self.base_path / output_dir
        self.cache_dir = self.base_path / cache_dir

        # Ensure directories exist
        for dir_path in [self.temp_dir, self.output_dir, self.cache_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_temp_path(self, job_id: str, filename: str) -> Path:
        """Get path for a temporary file."""
        job_temp_dir = self.temp_dir / job_id
        job_temp_dir.mkdir(parents=True, exist_ok=True)
        return job_temp_dir / filename

    def get_output_path(self, filename: str) -> Path:
        """Get path for an output file."""
        return self.output_dir / filename

    def get_cache_path(self, key: str) -> Path:
        """Get path for a cached file."""
        return self.cache_dir / key

    def cleanup_job_temp(self, job_id: str) -> None:
        """Remove temporary files for a job."""
        job_temp_dir = self.temp_dir / job_id
        if job_temp_dir.exists():
            try:
                shutil.rmtree(job_temp_dir)
                logger.info(f"Cleaned up temp files for job: {job_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup temp files for job {job_id}: {e}")

    def cleanup_old_temp_files(self, max_age_hours: int = 24) -> int:
        """
        Remove temporary files older than max_age_hours.

        Returns:
            Number of directories removed
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        removed_count = 0

        for item in self.temp_dir.iterdir():
            if item.is_dir():
                try:
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    if mtime < cutoff:
                        shutil.rmtree(item)
                        removed_count += 1
                        logger.info(f"Removed old temp directory: {item}")
                except Exception as e:
                    logger.error(f"Failed to remove temp directory {item}: {e}")

        return removed_count

    def cleanup_old_outputs(self, max_age_days: int = 7) -> int:
        """
        Remove output files older than max_age_days.

        Returns:
            Number of files removed
        """
        cutoff = datetime.now() - timedelta(days=max_age_days)
        removed_count = 0

        for item in self.output_dir.iterdir():
            if item.is_file():
                try:
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    if mtime < cutoff:
                        item.unlink()
                        removed_count += 1
                        logger.info(f"Removed old output file: {item}")
                except Exception as e:
                    logger.error(f"Failed to remove output file {item}: {e}")

        return removed_count

    def get_storage_stats(self) -> dict:
        """Get storage statistics."""
        def get_dir_size(path: Path) -> int:
            total = 0
            for item in path.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
            return total

        return {
            "temp_size_bytes": get_dir_size(self.temp_dir),
            "output_size_bytes": get_dir_size(self.output_dir),
            "cache_size_bytes": get_dir_size(self.cache_dir),
            "total_size_bytes": get_dir_size(self.base_path),
            "temp_files_count": sum(1 for _ in self.temp_dir.rglob("*") if _.is_file()),
            "output_files_count": sum(1 for _ in self.output_dir.glob("*") if _.is_file()),
        }

    def list_outputs(
        self,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "mtime",
        descending: bool = True
    ) -> List[dict]:
        """
        List output files.

        Args:
            limit: Maximum number of files to return
            offset: Number of files to skip
            sort_by: Sort field (name, mtime, size)
            descending: Sort order

        Returns:
            List of file info dictionaries
        """
        files = []

        for item in self.output_dir.iterdir():
            if item.is_file() and item.suffix.lower() == ".mp4":
                stat = item.stat()
                files.append({
                    "name": item.name,
                    "path": str(item),
                    "size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })

        # Sort
        if sort_by == "name":
            files.sort(key=lambda f: f["name"], reverse=descending)
        elif sort_by == "size":
            files.sort(key=lambda f: f["size_bytes"], reverse=descending)
        else:  # mtime
            files.sort(key=lambda f: f["modified_at"], reverse=descending)

        # Paginate
        return files[offset:offset + limit]

    def delete_output(self, filename: str) -> bool:
        """Delete an output file."""
        file_path = self.output_dir / filename
        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
                logger.info(f"Deleted output file: {filename}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete output file {filename}: {e}")
        return False
