import os
import sqlite3
import json
from datetime import datetime
from logger import setup_logger

# Setup database logger
db_logger = setup_logger('database', 'database.log')

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'ai_telemarketer.db')

def get_db_connection():
    """Create a connection to the SQLite database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        return conn
    except Exception as e:
        db_logger.error(f"Database connection error: {str(e)}")
        raise

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Create calls table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_sid TEXT UNIQUE,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT,
            caller_number TEXT,
            call_duration INTEGER
        )
        ''')
        
        # Create conversation entries table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id INTEGER,
            timestamp TIMESTAMP,
            role TEXT,  -- 'user' or 'assistant'
            content TEXT,
            FOREIGN KEY (call_id) REFERENCES calls (id)
        )
        ''')
        
        # Create performance metrics table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id INTEGER,
            step_name TEXT,  -- 'llm_processing', 'tts_processing', etc.
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_ms INTEGER,
            metadata TEXT,  -- JSON string for additional data
            FOREIGN KEY (call_id) REFERENCES calls (id)
        )
        ''')
        
        conn.commit()
        db_logger.info("Database initialized successfully")
    except Exception as e:
        db_logger.error(f"Database initialization error: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

def create_call(call_sid, caller_number):
    """Create a new call record in the database"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now()
        cursor.execute(
            "INSERT INTO calls (call_sid, start_time, status, caller_number) VALUES (?, ?, ?, ?)",
            (call_sid, now, "in-progress", caller_number)
        )
        call_id = cursor.lastrowid
        conn.commit()
        db_logger.info(f"Created new call record with ID: {call_id}")
        return call_id
    except Exception as e:
        db_logger.error(f"Error creating call record: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

def update_call_status(call_id, status, duration=None):
    """Update call status and optionally duration"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if status == "completed":
            now = datetime.now()
            cursor.execute(
                "UPDATE calls SET status = ?, end_time = ?, call_duration = ? WHERE id = ?",
                (status, now, duration, call_id)
            )
        else:
            cursor.execute(
                "UPDATE calls SET status = ? WHERE id = ?",
                (status, call_id)
            )
        conn.commit()
        db_logger.info(f"Updated call {call_id} status to {status}")
    except Exception as e:
        db_logger.error(f"Error updating call status: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

def add_conversation_entry(call_id, role, content):
    """Add a conversation entry (user input or assistant response)"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now()
        cursor.execute(
            "INSERT INTO conversation_entries (call_id, timestamp, role, content) VALUES (?, ?, ?, ?)",
            (call_id, now, role, content)
        )
        entry_id = cursor.lastrowid
        conn.commit()
        db_logger.info(f"Added conversation entry {entry_id} for call {call_id}")
        return entry_id
    except Exception as e:
        db_logger.error(f"Error adding conversation entry: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

def add_performance_metric(call_id, step_name, start_time, end_time, metadata=None):
    """Add a performance metric entry"""
    conn = get_db_connection()
    duration_ms = int((end_time - start_time).total_seconds() * 1000)
    metadata_json = json.dumps(metadata) if metadata else None
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO performance_metrics (call_id, step_name, start_time, end_time, duration_ms, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (call_id, step_name, start_time, end_time, duration_ms, metadata_json)
        )
        metric_id = cursor.lastrowid
        conn.commit()
        db_logger.info(f"Added performance metric {metric_id} for call {call_id}: {step_name} took {duration_ms}ms")
        return metric_id
    except Exception as e:
        db_logger.error(f"Error adding performance metric: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

def get_calls(limit=50, offset=0):
    """Get recent calls with pagination"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM calls 
            ORDER BY start_time DESC 
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        calls = [dict(row) for row in cursor.fetchall()]
        return calls
    finally:
        conn.close()

def get_call_details(call_id):
    """Get detailed info for a specific call"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Get call info
        cursor.execute("SELECT * FROM calls WHERE id = ?", (call_id,))
        call = dict(cursor.fetchone() or {})
        
        if not call:
            return None
            
        # Get conversation entries
        cursor.execute(
            "SELECT * FROM conversation_entries WHERE call_id = ? ORDER BY timestamp",
            (call_id,)
        )
        call['conversation'] = [dict(row) for row in cursor.fetchall()]
        
        # Get performance metrics
        cursor.execute(
            "SELECT * FROM performance_metrics WHERE call_id = ? ORDER BY start_time",
            (call_id,)
        )
        call['metrics'] = [dict(row) for row in cursor.fetchall()]
        
        return call
    finally:
        conn.close()

def get_performance_statistics():
    """Get aggregated performance statistics"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 
                step_name, 
                COUNT(*) as count, 
                AVG(duration_ms) as avg_duration,
                MIN(duration_ms) as min_duration,
                MAX(duration_ms) as max_duration
            FROM performance_metrics
            GROUP BY step_name
            ORDER BY avg_duration DESC
            """
        )
        stats = [dict(row) for row in cursor.fetchall()]
        return stats
    finally:
        conn.close()

def get_recent_calls(limit=5):
    """Get the most recent calls from the database"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM calls 
            ORDER BY start_time DESC 
            LIMIT ?
            """,
            (limit,)
        )
        calls = [dict(row) for row in cursor.fetchall()]
        return calls
    except Exception as e:
        db_logger.error(f"Error retrieving recent calls: {str(e)}")
        return None
    finally:
        conn.close()

def get_call_by_sid(call_sid):
    """Get call details using the Twilio call SID"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM calls WHERE call_sid = ?", (call_sid,))
        call = cursor.fetchone()
        if call:
            return dict(call)
        return None
    except Exception as e:
        db_logger.error(f"Error retrieving call by SID {call_sid}: {str(e)}")
        return None
    finally:
        conn.close()

def update_call_with_twilio_data(call_sid, twilio_data):
    """Update a call record with data from Twilio"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # First get the call ID from the call_sid
        cursor.execute("SELECT id FROM calls WHERE call_sid = ?", (call_sid,))
        result = cursor.fetchone()
        if not result:
            db_logger.error(f"No call found with SID {call_sid}")
            return False
            
        call_id = result['id']
        
        # Update the call record
        cursor.execute(
            """
            UPDATE calls SET 
            status = ?,
            call_duration = ?
            WHERE id = ?
            """,
            (twilio_data.get('status', 'unknown'), twilio_data.get('duration', 0), call_id)
        )
        
        if twilio_data.get('status') == 'completed' and 'end_time' not in twilio_data:
            cursor.execute(
                "UPDATE calls SET end_time = ? WHERE id = ?",
                (datetime.now(), call_id)
            )
            
        conn.commit()
        db_logger.info(f"Updated call {call_id} with Twilio data")
        return True
    except Exception as e:
        db_logger.error(f"Error updating call with Twilio data: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

# Initialize database when module is imported
init_db()
