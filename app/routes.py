# app/routes.py

from flask import render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import uuid
from app import app
from app.utils import process_orthophotos, is_allowed_file

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    files = request.files.getlist('files[]')
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    # Créer un ID unique pour cette session d'upload
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    uploaded_files = []
    for file in files:
        if file and is_allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(session_dir, filename)
            file.save(file_path)
            uploaded_files.append(file_path)
    
    if not uploaded_files:
        return jsonify({'error': 'Aucun fichier valide. Formats acceptés: .tif, .tiff'}), 400
    
    # Traiter les orthophotos
    try:
        map_path = process_orthophotos(uploaded_files, session_id)
        return jsonify({
            'success': True, 
            'map_url': url_for('show_map', session_id=session_id),
            'files_count': len(uploaded_files)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/map/<session_id>')
def show_map(session_id):
    map_path = os.path.join(app.config['UPLOAD_FOLDER'], session_id, 'map.html')
    if not os.path.exists(map_path):
        flash('Carte non trouvée', 'error')
        return redirect(url_for('index'))
    
    return render_template('map.html', session_id=session_id)

@app.route('/maps/<session_id>/map.html')
def serve_map(session_id):
    map_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    return send_from_directory(map_dir, 'map.html')