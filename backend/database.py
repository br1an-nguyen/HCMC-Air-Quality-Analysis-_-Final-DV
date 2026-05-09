import sqlite3
import json
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "ai_logs.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_prompt TEXT,
            generated_code TEXT,
            explanation TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            executed_code TEXT,
            stdout TEXT,
            stderr TEXT,
            success BOOLEAN
        )
    ''')
    conn.commit()
    conn.close()

def log_chat(user_prompt: str, generated_code: str, explanation: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO chat_logs (user_prompt, generated_code, explanation) VALUES (?, ?, ?)',
              (user_prompt, generated_code, explanation))
    conn.commit()
    conn.close()

def log_execution(executed_code: str, stdout: str, stderr: str, success: bool):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO execution_logs (executed_code, stdout, stderr, success) VALUES (?, ?, ?, ?)',
              (executed_code, stdout, stderr, success))
    conn.commit()
    conn.close()

init_db()
