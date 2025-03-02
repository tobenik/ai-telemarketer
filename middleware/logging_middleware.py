import time
from flask import g, request
from typing import Optional, Callable

class LoggingMiddleware:
    def __init__(self, logger):
        self.logger = logger
    
    def before_request(self):
        """Store the start time of the request"""
        g.start_time = time.time()
    
    def after_request(self, response):
        """Log request and response details"""
        duration_ms = int((time.time() - g.start_time) * 1000)
        
        log_data = {
            'req_type': f"{request.method} {request.path}",
            'status_code': response.status_code,
            'duration_ms': duration_ms,
            'ip_addr': request.remote_addr
        }
        
        # Choose the appropriate log formatter based on the request path
        if request.path == "/answer":
            self._log_twilio_request(log_data)
        else:
            self._log_standard_request(log_data)
        
        return response
    
    def _log_standard_request(self, log_data):
        """Format and log standard requests"""
        self.logger.info(
            f"REQ: {log_data['req_type']} | "
            f"STATUS: {log_data['status_code']} | "
            f"DURATION: {log_data['duration_ms']}ms | "
            f"IP: {log_data['ip_addr']}"
        )
    
    def _log_twilio_request(self, log_data):
        """Format and log Twilio-specific requests"""
        call_sid = request.values.get('CallSid', 'Unknown')
        from_number = request.values.get('From', 'Unknown')
        
        self.logger.info(
            f"REQ: {log_data['req_type']} | "
            f"STATUS: {log_data['status_code']} | "
            f"DURATION: {log_data['duration_ms']}ms | "
            f"IP: {log_data['ip_addr']} | "
            f"CALL_FROM: {from_number} | "
            f"SID: {call_sid}"
        )

def setup_logging_middleware(app, logger):
    """Configure the Flask application with logging middleware"""
    middleware = LoggingMiddleware(logger)
    
    app.before_request(middleware.before_request)
    app.after_request(middleware.after_request)
    
    return middleware
