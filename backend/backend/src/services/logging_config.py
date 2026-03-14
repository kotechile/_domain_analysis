"""
Structured logging configuration for async operations
"""

import structlog
import logging
import sys
from typing import Any, Dict
from datetime import datetime


def configure_async_logging():
    """Configure structured logging for async operations"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # Set specific loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.WARNING)


def get_async_logger(name: str) -> structlog.BoundLogger:
    """Get structured logger for async operations"""
    return structlog.get_logger(name)


class AsyncOperationLogger:
    """Logger specifically for async operations with context tracking"""
    
    def __init__(self, operation_name: str, domain: str = None):
        self.logger = get_async_logger("async_operations")
        self.operation_name = operation_name
        self.domain = domain
        self.start_time = datetime.utcnow()
        self.context = {
            "operation": operation_name,
            "domain": domain,
            "start_time": self.start_time.isoformat()
        }
    
    def log_task_start(self, task_id: str, task_type: str, **kwargs):
        """Log async task start"""
        self.logger.info(
            "Async task started",
            task_id=task_id,
            task_type=task_type,
            **self.context,
            **kwargs
        )
    
    def log_task_progress(self, task_id: str, progress_percentage: int, 
                         current_operation: str = None, **kwargs):
        """Log async task progress"""
        self.logger.info(
            "Async task progress",
            task_id=task_id,
            progress_percentage=progress_percentage,
            current_operation=current_operation,
            **self.context,
            **kwargs
        )
    
    def log_task_completion(self, task_id: str, duration_seconds: float = None, **kwargs):
        """Log async task completion"""
        if duration_seconds is None:
            duration_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        self.logger.info(
            "Async task completed",
            task_id=task_id,
            duration_seconds=duration_seconds,
            **self.context,
            **kwargs
        )
    
    def log_task_error(self, task_id: str, error: str, retry_count: int = 0, **kwargs):
        """Log async task error"""
        self.logger.error(
            "Async task failed",
            task_id=task_id,
            error=error,
            retry_count=retry_count,
            **self.context,
            **kwargs
        )
    
    def log_data_collection(self, data_type: str, record_count: int = None, **kwargs):
        """Log data collection progress"""
        self.logger.info(
            "Data collection progress",
            data_type=data_type,
            record_count=record_count,
            **self.context,
            **kwargs
        )
    
    def log_cache_operation(self, operation: str, cache_key: str, hit: bool = None, **kwargs):
        """Log cache operations"""
        self.logger.info(
            "Cache operation",
            operation=operation,
            cache_key=cache_key,
            cache_hit=hit,
            **self.context,
            **kwargs
        )
    
    def log_cost_metrics(self, api_calls: int, estimated_cost: float, **kwargs):
        """Log cost metrics for async operations"""
        self.logger.info(
            "Cost metrics",
            api_calls=api_calls,
            estimated_cost=estimated_cost,
            **self.context,
            **kwargs
        )
    
    def log_dual_mode_decision(self, chosen_mode: str, reason: str, **kwargs):
        """Log dual mode decision making"""
        self.logger.info(
            "Dual mode decision",
            chosen_mode=chosen_mode,
            reason=reason,
            **self.context,
            **kwargs
        )


class ProgressTracker:
    """Track progress for async operations with sub-operations support"""
    
    def __init__(self, total_operations: int, operation_name: str, domain: str = None):
        self.logger = get_async_logger("progress_tracker")
        self.total_operations = total_operations
        self.completed_operations = 0
        self.operation_name = operation_name
        self.domain = domain
        self.start_time = datetime.utcnow()
        self.operations = []
        self.sub_operations = {}  # Track sub-operations within main operations
    
    def add_operation(self, operation: str):
        """Add operation to track"""
        self.operations.append({
            "name": operation,
            "status": "pending",
            "start_time": None,
            "end_time": None
        })
    
    def start_operation(self, operation: str):
        """Mark operation as started"""
        for op in self.operations:
            if op["name"] == operation:
                op["status"] = "in_progress"
                op["start_time"] = datetime.utcnow()
                break
        
        self.logger.info(
            "Operation started",
            operation=operation,
            progress_percentage=self.get_progress_percentage(),
            **self._get_context()
        )
    
    def complete_operation(self, operation: str):
        """Mark operation as completed"""
        for op in self.operations:
            if op["name"] == operation:
                op["status"] = "completed"
                op["end_time"] = datetime.utcnow()
                self.completed_operations += 1
                break
        
        self.logger.info(
            "Operation completed",
            operation=operation,
            progress_percentage=self.get_progress_percentage(),
            **self._get_context()
        )
    
    def fail_operation(self, operation: str, error: str):
        """Mark operation as failed"""
        for op in self.operations:
            if op["name"] == operation:
                op["status"] = "failed"
                op["end_time"] = datetime.utcnow()
                op["error"] = error
                break
        
        self.logger.error(
            "Operation failed",
            operation=operation,
            error=error,
            progress_percentage=self.get_progress_percentage(),
            **self._get_context()
        )
    
    def add_sub_operation(self, main_operation: str, sub_operation: str):
        """Add a sub-operation to track within a main operation"""
        if main_operation not in self.sub_operations:
            self.sub_operations[main_operation] = []
        self.sub_operations[main_operation].append({
            "name": sub_operation,
            "status": "pending",
            "start_time": None,
            "end_time": None
        })
    
    def start_sub_operation(self, main_operation: str, sub_operation: str):
        """Mark sub-operation as started"""
        if main_operation in self.sub_operations:
            for sub_op in self.sub_operations[main_operation]:
                if sub_op["name"] == sub_operation:
                    sub_op["status"] = "in_progress"
                    sub_op["start_time"] = datetime.utcnow()
                    break
        
        self.logger.info(
            "Sub-operation started",
            operation=main_operation,
            sub_operation=sub_operation,
            progress_percentage=self.get_progress_percentage(),
            **self._get_context()
        )
    
    def complete_sub_operation(self, main_operation: str, sub_operation: str):
        """Mark sub-operation as completed"""
        if main_operation in self.sub_operations:
            for sub_op in self.sub_operations[main_operation]:
                if sub_op["name"] == sub_operation:
                    sub_op["status"] = "completed"
                    sub_op["end_time"] = datetime.utcnow()
                    break
        
        self.logger.info(
            "Sub-operation completed",
            operation=main_operation,
            sub_operation=sub_operation,
            progress_percentage=self.get_progress_percentage(),
            **self._get_context()
        )
    
    def get_progress_percentage(self) -> int:
        """Get current progress percentage including sub-operations with weighted phases"""
        if self.total_operations == 0:
            return 100
        
        # Define weighted progress for each main operation
        operation_weights = {
            "essential_data": 25,      # 0% -> 25%
            "detailed_data": 45,       # 25% -> 70% (45% of total)
            "ai_analysis": 20,         # 70% -> 90% (20% of total)
            "finalization": 10         # 90% -> 100% (10% of total)
        }
        
        # Calculate base progress from completed main operations
        base_progress = 0
        for i, op in enumerate(self.operations):
            if op["status"] == "completed":
                # Add weight for completed operations
                if i == 0:  # essential_data
                    base_progress += operation_weights["essential_data"]
                elif i == 1:  # detailed_data
                    base_progress += operation_weights["detailed_data"]
                elif i == 2:  # ai_analysis
                    base_progress += operation_weights["ai_analysis"]
                elif i == 3:  # finalization
                    base_progress += operation_weights["finalization"]
        
        # Add sub-operation progress for the current main operation
        current_operation = self.get_current_operation()
        if current_operation and current_operation in self.sub_operations:
            sub_ops = self.sub_operations[current_operation]
            if sub_ops:
                completed_sub_ops = sum(1 for sub_op in sub_ops if sub_op["status"] == "completed")
                total_sub_ops = len(sub_ops)
                
                # Calculate sub-operation progress within the current operation's weight
                if current_operation == "detailed_data":
                    sub_progress = (completed_sub_ops / total_sub_ops) * operation_weights["detailed_data"]
                    base_progress += sub_progress
                elif current_operation == "ai_analysis":
                    sub_progress = (completed_sub_ops / total_sub_ops) * operation_weights["ai_analysis"]
                    base_progress += sub_progress
        
        return int(min(base_progress, 100))
    
    def get_estimated_time_remaining(self) -> int:
        """Get estimated time remaining in seconds"""
        if self.completed_operations == 0:
            return None
        
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        avg_time_per_operation = elapsed / self.completed_operations
        remaining_operations = self.total_operations - self.completed_operations
        
        return int(avg_time_per_operation * remaining_operations)
    
    def get_completed_operations(self) -> list:
        """Get list of completed operations"""
        return [op["name"] for op in self.operations if op["status"] == "completed"]
    
    def get_current_operation(self) -> str:
        """Get currently running operation"""
        for op in self.operations:
            if op["status"] == "in_progress":
                return op["name"]
        return None
    
    def _get_context(self) -> Dict[str, Any]:
        """Get logging context"""
        return {
            "operation_name": self.operation_name,
            "domain": self.domain,
            "total_operations": self.total_operations,
            "completed_operations": self.completed_operations,
            "estimated_time_remaining": self.get_estimated_time_remaining()
        }


# Initialize logging on module import
configure_async_logging()




