import sqlite3
import hashlib
from datetime import datetime
import streamlit as st
import os
import uuid
from PIL import Image
import numpy as np
import json

def get_connection():
    """Membuat koneksi ke database SQLite"""
    return sqlite3.connect('chili_detection.db', check_same_thread=False)

def init_database():
    """Inisialisasi database dan tabel yang diperlukan"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabel users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("PRAGMA table_info(detection_history)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'detection_history' not in [table[0] for table in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detection_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                image_name TEXT NOT NULL,
                prediction TEXT NOT NULL,
                confidence REAL NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                image_path TEXT,
                detection_details TEXT,
                FOREIGN KEY (username) REFERENCES users (username)
            )
        ''')
    else:
        if 'image_path' not in columns:
            cursor.execute('ALTER TABLE detection_history ADD COLUMN image_path TEXT')
        
        if 'detection_details' not in columns:
            cursor.execute('ALTER TABLE detection_history ADD COLUMN detection_details TEXT')
    
    if not os.path.exists('detection_images'):
        os.makedirs('detection_images')
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password menggunakan SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password):
    """Autentikasi user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    password_hash = hash_password(password)
    cursor.execute(
        "SELECT username FROM users WHERE username = ? AND password_hash = ?",
        (username, password_hash)
    )
    
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def register_user(username, password):
    """Registrasi user baru"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def save_detection_image(image):
    """Simpan gambar hasil deteksi dan kembalikan path-nya"""
    filename = f"detection_{uuid.uuid4().hex}.jpg"
    filepath = os.path.join('detection_images', filename)
    
    if isinstance(image, Image.Image):
        image.save(filepath, quality=95, optimize=True)  
    else:
        return None
    
    return filepath

def save_detection_result(username, image_name, prediction, confidence, detection_time=None, detection_image=None, detection_details=None):
    """Simpan hasil deteksi ke database dengan timestamp custom, gambar hasil deteksi, dan detail deteksi"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if detection_time is None:
        detection_time = datetime.now()
    
    timestamp_str = detection_time.strftime('%Y-%m-%d %H:%M:%S')
    
    image_path = None
    if detection_image is not None:
        image_path = save_detection_image(detection_image)
    
    details_json = None
    if detection_details is not None:
        details_json = json.dumps(detection_details)
    
    cursor.execute("PRAGMA table_info(detection_history)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'detection_details' in columns:
        cursor.execute(
            "INSERT INTO detection_history (username, image_name, prediction, confidence, timestamp, image_path, detection_details) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (username, image_name, prediction, confidence, timestamp_str, image_path, details_json)
        )
    elif 'image_path' in columns:
        cursor.execute(
            "INSERT INTO detection_history (username, image_name, prediction, confidence, timestamp, image_path) VALUES (?, ?, ?, ?, ?, ?)",
            (username, image_name, prediction, confidence, timestamp_str, image_path)
        )
    else:
        cursor.execute(
            "INSERT INTO detection_history (username, image_name, prediction, confidence, timestamp) VALUES (?, ?, ?, ?, ?)",
            (username, image_name, prediction, confidence, timestamp_str)
        )
    
    conn.commit()
    conn.close()

def get_user_history(username):
    """Ambil riwayat deteksi user dengan ID, path gambar, dan detail deteksi"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(detection_history)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'detection_details' in columns and 'image_path' in columns:
        cursor.execute(
            "SELECT id, image_name, prediction, confidence, timestamp, image_path, detection_details FROM detection_history WHERE username = ? ORDER BY timestamp DESC",
            (username,)
        )
    elif 'image_path' in columns:
        cursor.execute(
            "SELECT id, image_name, prediction, confidence, timestamp, image_path, NULL FROM detection_history WHERE username = ? ORDER BY timestamp DESC",
            (username,)
        )
    else:
        cursor.execute(
            "SELECT id, image_name, prediction, confidence, timestamp, NULL, NULL FROM detection_history WHERE username = ? ORDER BY timestamp DESC",
            (username,)
        )
    
    results = cursor.fetchall()
    conn.close()
    
    return results

def delete_detection_by_id(detection_id, username):
    """Hapus deteksi berdasarkan ID dan username (untuk keamanan)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(detection_history)")
    columns = [column[1] for column in cursor.fetchall()]
    
    image_path = None
    if 'image_path' in columns:
        cursor.execute(
            "SELECT image_path FROM detection_history WHERE id = ? AND username = ?",
            (detection_id, username)
        )
        
        result = cursor.fetchone()
        
        if result and result[0]:
            image_path = result[0]
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except:
                    pass  
    
    cursor.execute(
        "DELETE FROM detection_history WHERE id = ? AND username = ?",
        (detection_id, username)
    )
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return rows_affected > 0

def delete_all_user_history(username):
    """Hapus semua riwayat deteksi user dan file gambar terkait"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(detection_history)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'image_path' in columns:
        cursor.execute(
            "SELECT image_path FROM detection_history WHERE username = ?",
            (username,)
        )
        
        results = cursor.fetchall()
        
        for result in results:
            if result[0]:
                image_path = result[0]
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except:
                        pass  

    cursor.execute(
        "DELETE FROM detection_history WHERE username = ?",
        (username,)
    )
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return rows_affected

def delete_multiple_detections(detection_ids, username):
    """Hapus multiple deteksi berdasarkan list ID dan file gambar terkait"""
    if not detection_ids:
        return 0
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(detection_history)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'image_path' in columns:
        placeholders = ','.join(['?' for _ in detection_ids])
        query = f"SELECT image_path FROM detection_history WHERE id IN ({placeholders}) AND username = ?"
        
        cursor.execute(query, detection_ids + [username])
        
        results = cursor.fetchall()
        
        for result in results:
            if result[0]:
                image_path = result[0]
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except:
                        pass  
    
    placeholders = ','.join(['?' for _ in detection_ids])
    query = f"DELETE FROM detection_history WHERE id IN ({placeholders}) AND username = ?"
    cursor.execute(query, detection_ids + [username])
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return rows_affected