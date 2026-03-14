"""
Robust date parsing utilities
"""

import datetime
from typing import Optional, Union
from dateutil import parser
import structlog

logger = structlog.get_logger()

def parse_iso_datetime(dt_str: Union[str, datetime.datetime]) -> Optional[datetime.datetime]:
    """
    Robustly parse ISO datetime strings, handling variable fractional seconds
    and timezone offsets that Python 3.10's fromisoformat might struggle with.
    """
    if dt_str is None:
        return None
        
    if isinstance(dt_str, datetime.datetime):
        return dt_str
        
    if not isinstance(dt_str, str):
        logger.warning("Attempted to parse non-string datetime", type=type(dt_str), value=dt_str)
        return None

    try:
        # Standardize 'Z' to '+00:00'
        dt_str = dt_str.replace('Z', '+00:00')
        
        # Use dateutil parser which is much more robust than datetime.fromisoformat
        # handles variable microseconds (1-6 digits) and timezone offsets
        return parser.isoparse(dt_str)
    except Exception as e:
        logger.warning("Failed to parse ISO datetime", timestamp=dt_str, error=str(e))
        try:
            # Fallback to general purpose parser if isoparse fails
            return parser.parse(dt_str)
        except Exception as e2:
            logger.error("All datetime parsing attempts failed", timestamp=dt_str, error=str(e2))
            return None

def format_iso_datetime(dt: Optional[datetime.datetime]) -> Optional[str]:
    """Format datetime as ISO string with UTC 'Z' or offset"""
    if dt is None:
        return None
    return dt.isoformat()
