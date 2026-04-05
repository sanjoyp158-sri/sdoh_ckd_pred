"""
Audit logging middleware for tracking data access.
Minimal implementation for HIPAA compliance.
"""

from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class AuditLogEntry:
    """Audit log entry for data access."""
    user_id: str
    username: str
    action: str  # 'read', 'write', 'delete', 'predict'
    resource_type: str  # 'patient', 'prediction', 'acknowledgment'
    resource_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    data_elements: List[str] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None
    
    def __repr__(self):
        return (
            f"AuditLog({self.timestamp.isoformat()}, "
            f"user={self.username}, action={self.action}, "
            f"resource={self.resource_type}/{self.resource_id}, "
            f"success={self.success})"
        )


class AuditLogger:
    """
    Audit logger for tracking all data access events.
    
    In production, this would write to a separate audit database
    or secure logging service. For minimal implementation, logs
    to application logger and maintains in-memory store.
    """
    
    def __init__(self):
        """Initialize audit logger."""
        self._logs: List[AuditLogEntry] = []
    
    def log_access(
        self,
        user_id: str,
        username: str,
        action: str,
        resource_type: str,
        resource_id: str,
        data_elements: Optional[List[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> AuditLogEntry:
        """
        Log a data access event.
        
        Args:
            user_id: User ID performing the action
            username: Username performing the action
            action: Action type (read, write, delete, predict)
            resource_type: Type of resource accessed
            resource_id: ID of resource accessed
            data_elements: List of data elements accessed
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether the action succeeded
            error_message: Error message if action failed
            
        Returns:
            AuditLogEntry that was created
        """
        entry = AuditLogEntry(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            timestamp=datetime.now(),
            ip_address=ip_address,
            user_agent=user_agent,
            data_elements=data_elements or [],
            success=success,
            error_message=error_message
        )
        
        # Store in memory
        self._logs.append(entry)
        
        # Log to application logger
        log_msg = (
            f"AUDIT: user={username} ({user_id}), action={action}, "
            f"resource={resource_type}/{resource_id}, "
            f"elements={data_elements}, success={success}"
        )
        
        if success:
            logger.info(log_msg)
        else:
            logger.warning(f"{log_msg}, error={error_message}")
        
        return entry
    
    def get_logs(
        self,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """
        Retrieve audit logs with optional filtering.
        
        Args:
            user_id: Filter by user ID
            resource_id: Filter by resource ID
            action: Filter by action type
            limit: Maximum number of logs to return
            
        Returns:
            List of matching audit log entries
        """
        filtered_logs = self._logs
        
        if user_id:
            filtered_logs = [log for log in filtered_logs if log.user_id == user_id]
        
        if resource_id:
            filtered_logs = [log for log in filtered_logs if log.resource_id == resource_id]
        
        if action:
            filtered_logs = [log for log in filtered_logs if log.action == action]
        
        # Return most recent first
        return sorted(filtered_logs, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def clear_logs(self):
        """Clear all audit logs (for testing only)."""
        self._logs.clear()


# Global audit logger instance
audit_logger = AuditLogger()
