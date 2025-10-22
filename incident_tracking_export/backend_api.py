"""
============================================================
INCIDENT TRACKING SYSTEM - BACKEND API
============================================================
Flask API endpoints for production incident management
Supports: CRUD operations, notes, screenshots, filtering
============================================================

INTEGRATION INSTRUCTIONS:
1. Add these routes to your Flask app.py
2. Ensure you have a get_connection() function that returns a PostgreSQL connection
3. Import required modules: Flask, request, jsonify, Response, mimetypes
4. Database connection should use psycopg2 or similar PostgreSQL driver

Example get_connection() function:
    import psycopg2
    def get_connection():
        return psycopg2.connect(os.getenv('DATABASE_URL'))
"""

from flask import request, jsonify, Response
import mimetypes

# ============================================================
# GET ALL INCIDENTS (with optional filtering)
# ============================================================
@app.route('/api/incidents', methods=['GET'])
def get_incidents():
    """Get all production incidents with optional filtering by status and severity"""
    try:
        status_filter = request.args.get('status')
        severity_filter = request.args.get('severity')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, title, description, severity, status, reported_by, created_at, updated_at, cause, resolution
            FROM production_incidents
            WHERE 1=1
        """
        params = []
        
        if status_filter:
            query += " AND status = %s"
            params.append(status_filter)
        
        if severity_filter:
            query += " AND severity = %s"
            params.append(severity_filter)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        incidents = cursor.fetchall()
        
        result = []
        for inc in incidents:
            # Get notes for this incident
            cursor.execute("""
                SELECT id, note_type, note, created_by, created_at
                FROM incident_notes
                WHERE incident_id = %s
                ORDER BY created_at DESC
            """, (inc[0],))
            notes = cursor.fetchall()
            
            result.append({
                'id': inc[0],
                'title': inc[1],
                'description': inc[2],
                'severity': inc[3],
                'status': inc[4],
                'reported_by': inc[5],
                'created_at': inc[6].isoformat() if inc[6] else None,
                'updated_at': inc[7].isoformat() if inc[7] else None,
                'cause': inc[8],
                'resolution': inc[9],
                'notes': [{
                    'id': n[0],
                    'note_type': n[1],
                    'note': n[2],
                    'created_by': n[3],
                    'created_at': n[4].isoformat() if n[4] else None
                } for n in notes]
            })
        
        conn.close()
        return jsonify({'success': True, 'incidents': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# CREATE NEW INCIDENT
# ============================================================
@app.route('/api/incidents', methods=['POST'])
def create_incident():
    """Create a new production incident"""
    try:
        data = request.json
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        severity = data.get('severity', 'medium')
        reported_by = data.get('reported_by', 'System')
        
        if not title or not description:
            return jsonify({'success': False, 'error': 'Title and description required'}), 400
        
        if severity not in ['low', 'medium', 'high', 'critical']:
            return jsonify({'success': False, 'error': 'Invalid severity'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO production_incidents (title, description, severity, reported_by, status)
            VALUES (%s, %s, %s, %s, 'new')
            RETURNING id
        """, (title, description, severity, reported_by))
        
        incident_id = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'incident_id': incident_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# UPDATE INCIDENT (status or full edit)
# ============================================================
@app.route('/api/incidents/<int:incident_id>', methods=['PUT'])
def update_incident(incident_id):
    """Update incident status or full details (title, description, severity, cause, resolution)"""
    try:
        data = request.json
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if this is a status-only update or a full edit
        if 'status' in data and len(data) == 1:
            # Status-only update (quick status dropdown change)
            status = data.get('status')
            if not status or status not in ['new', 'in_progress', 'resolved', 'closed']:
                return jsonify({'success': False, 'error': 'Invalid status'}), 400
            
            cursor.execute("""
                UPDATE production_incidents
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (status, incident_id))
            
            if cursor.rowcount == 0:
                conn.close()
                return jsonify({'success': False, 'error': f'Incident {incident_id} not found'}), 404
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'incident_id': incident_id, 'status': status})
        else:
            # Full edit update (from edit modal)
            title = data.get('title')
            description = data.get('description')
            severity = data.get('severity')
            cause = data.get('cause', '').strip() or None
            resolution = data.get('resolution', '').strip() or None
            
            if not title or not description or not severity:
                return jsonify({'success': False, 'error': 'Missing required fields'}), 400
            
            if severity not in ['low', 'medium', 'high', 'critical']:
                return jsonify({'success': False, 'error': 'Invalid severity'}), 400
            
            cursor.execute("""
                UPDATE production_incidents
                SET title = %s, description = %s, severity = %s, cause = %s, resolution = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (title, description, severity, cause, resolution, incident_id))
            
            if cursor.rowcount == 0:
                conn.close()
                return jsonify({'success': False, 'error': f'Incident {incident_id} not found'}), 404
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'incident_id': incident_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# ADD NOTE TO INCIDENT
# ============================================================
@app.route('/api/incidents/<int:incident_id>/notes', methods=['POST'])
def add_incident_note(incident_id):
    """Add a note/update to an incident timeline"""
    try:
        data = request.json
        note = data.get('note', '').strip()
        note_type = data.get('note_type', 'system')
        created_by = data.get('created_by', 'System')
        
        if not note:
            return jsonify({'success': False, 'error': 'Note content required'}), 400
        
        if note_type not in ['user', 'system']:
            note_type = 'system'
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verify incident exists
        cursor.execute("""
            SELECT id FROM production_incidents WHERE id = %s
        """, (incident_id,))
        
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': f'Incident {incident_id} not found'}), 404
        
        cursor.execute("""
            INSERT INTO incident_notes (incident_id, note_type, note, created_by)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (incident_id, note_type, note, created_by))
        
        note_id = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'note_id': note_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# ATTACH SCREENSHOT TO INCIDENT
# ============================================================
@app.route('/api/incidents/<int:incident_id>/screenshots', methods=['POST'])
def attach_incident_screenshot(incident_id):
    """Attach a screenshot to an incident (stores in database as BYTEA)"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        uploaded_by = request.form.get('uploaded_by', 'System')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Validate file size (16MB max)
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 16 * 1024 * 1024:
            return jsonify({'success': False, 'error': 'File too large (max 16MB)'}), 400
        
        file_data = file.read()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verify incident exists
        cursor.execute("""
            SELECT id FROM production_incidents WHERE id = %s
        """, (incident_id,))
        
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': f'Incident {incident_id} not found'}), 404
        
        cursor.execute("""
            INSERT INTO production_incident_screenshots (incident_id, filename, file_data, uploaded_by)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (incident_id, file.filename, file_data, uploaded_by))
        
        screenshot_id = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'screenshot_id': screenshot_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# GET SCREENSHOTS FOR INCIDENT
# ============================================================
@app.route('/api/incidents/<int:incident_id>/screenshots', methods=['GET'])
def get_incident_screenshots(incident_id):
    """Get all screenshots metadata for an incident"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, filename, uploaded_by, uploaded_at
            FROM production_incident_screenshots
            WHERE incident_id = %s
            ORDER BY uploaded_at DESC
        """, (incident_id,))
        
        screenshots = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'screenshots': [{
                'id': s[0],
                'filename': s[1],
                'uploaded_by': s[2],
                'uploaded_at': s[3].isoformat() if s[3] else None
            } for s in screenshots]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# GET SPECIFIC SCREENSHOT BINARY DATA
# ============================================================
@app.route('/api/screenshots/<int:screenshot_id>', methods=['GET'])
def get_screenshot_data(screenshot_id):
    """Get screenshot binary data for display"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT filename, file_data
            FROM production_incident_screenshots
            WHERE id = %s
        """, (screenshot_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'success': False, 'error': 'Screenshot not found'}), 404
        
        filename, file_data = result
        
        mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        
        return Response(
            bytes(file_data),
            mimetype=mime_type,
            headers={'Content-Disposition': f'inline; filename="{filename}"'}
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# DELETE SCREENSHOT
# ============================================================
@app.route('/api/screenshots/<int:screenshot_id>', methods=['DELETE'])
def delete_screenshot(screenshot_id):
    """Delete a screenshot from an incident"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM production_incident_screenshots
            WHERE id = %s
        """, (screenshot_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Screenshot not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
