from flask import Blueprint, render_template, jsonify, request
import database as db
from logger import setup_logger
import sqlite3

# Setup admin logger
admin_logger = setup_logger('admin', 'admin.log')

# Create a Flask Blueprint for the admin routes
admin_bp = Blueprint('admin', __name__, 
                    template_folder='templates',
                    static_folder='static',
                    url_prefix='/admin')

@admin_bp.route('/')
def index():
    """Admin portal home page"""
    return render_template('admin/index.html')

@admin_bp.route('/api/calls')
def get_calls():
    """API endpoint to get call data"""
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    
    try:
        calls = db.get_calls(limit, offset)
        return jsonify({"success": True, "calls": calls})
    except sqlite3.Error as e:
        admin_logger.error(f"Database error getting calls: {str(e)}")
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        admin_logger.error(f"Error getting calls: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/calls/<int:call_id>')
def get_call_details(call_id):
    """API endpoint to get detailed call data"""
    try:
        call = db.get_call_details(call_id)
        if call:
            return jsonify({"success": True, "call": call})
        else:
            return jsonify({"success": False, "error": "Call not found"}), 404
    except sqlite3.Error as e:
        admin_logger.error(f"Database error getting call details: {str(e)}")
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        admin_logger.error(f"Error getting call details: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/performance')
def get_performance():
    """API endpoint to get performance metrics"""
    try:
        stats = db.get_performance_statistics()
        return jsonify({"success": True, "stats": stats})
    except sqlite3.Error as e:
        admin_logger.error(f"Database error getting performance stats: {str(e)}")
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        admin_logger.error(f"Error getting performance stats: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/db/stats')
def get_db_stats():
    """API endpoint to get database statistics"""
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # Get table counts
        stats = {}
        tables = ['calls', 'conversation_entries', 'performance_metrics']
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        
        # Get active calls count
        cursor.execute("SELECT COUNT(*) FROM calls WHERE status = 'in-progress'")
        stats['active_calls'] = cursor.fetchone()[0]
        
        # Get database file size
        import os
        if os.path.exists(db.DATABASE_PATH):
            stats['db_size'] = os.path.getsize(db.DATABASE_PATH) / (1024 * 1024)  # Size in MB
        else:
            stats['db_size'] = 0
        
        conn.close()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        admin_logger.error(f"Error getting database stats: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/call/<int:call_id>')
def call_detail(call_id):
    """Admin page for detailed call information"""
    return render_template('admin/call_detail.html', call_id=call_id)

@admin_bp.route('/system')
def system():
    """System status page"""
    return render_template('admin/system.html')

@admin_bp.app_template_filter('format_timestamp')
def format_timestamp(timestamp):
    """Format timestamp for display in templates"""
    from datetime import datetime
    if not timestamp:
        return "N/A"
    try:
        dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        try:
            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return timestamp
