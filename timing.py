import time
import functools
from datetime import datetime
from contextlib import contextmanager

@contextmanager
def measure_time(call_id, step_name, store_func, metadata=None):
    """
    Context manager to measure execution time of a block of code
    
    Args:
        call_id: ID of the current call
        step_name: Name of the step being measured
        store_func: Function to store the timing data
        metadata: Optional metadata to store with the timing
    """
    start_time = datetime.now()
    try:
        yield
    finally:
        end_time = datetime.now()
        if store_func and callable(store_func):
            store_func(call_id, step_name, start_time, end_time, metadata)

def time_function(step_name):
    """
    Decorator to measure execution time of a function
    
    Args:
        step_name: Name of the step being measured
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract call_id from kwargs or use None
            call_id = kwargs.get('call_id')
            
            # Access the store_func from the instance if available
            store_func = None
            if args and hasattr(args[0], 'store_performance_metric'):
                store_func = args[0].store_performance_metric
                
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = datetime.now()
                if store_func and callable(store_func) and call_id:
                    metadata = {'function': func.__name__}
                    store_func(call_id, step_name, start_time, end_time, metadata)
                    
        return wrapper
    return decorator
