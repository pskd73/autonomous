import logging
from typing import Callable

logger = logging.getLogger(__name__)

def side_effect(function: Callable, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except Exception as e:
        logger.error(f"Side effect: {e}")
        return None