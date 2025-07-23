import sqlite3
from cryptography.fernet import Fernet
import os

DB_NAME = "equipamentos.db"
KEY_FILE = "secret.key"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    # Cria tabela se não existir
    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS equipamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                ip TEXT,
                usuario TEXT,
                senha TEXT
            )
        ''')
    # Gera chave Fernet se não existir
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)

def encrypt_password(password: str) -> str:
    with open(KEY_FILE, 'rb') as f:
        key = f.read()
    fernet = Fernet(key)
    token = fernet.encrypt(password.encode())
    return token.decode()

def decrypt_password(token: str) -> str:
    with open(KEY_FILE, 'rb') as f:
        key = f.read()
    fernet = Fernet(key)
    return fernet.decrypt(token.encode()).decode()

def add_equipamento(nome: str, ip: str, usuario: str, senha: str):
    senha_cript = encrypt_password(senha)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO equipamentos (nome, ip, usuario, senha) VALUES (?, ?, ?, ?)",
            (nome, ip, usuario, senha_cript)
        )

def get_equipamentos():
    with get_connection() as conn:
        cursor = conn.execute("SELECT id, nome, ip, usuario FROM equipamentos")
        return cursor.fetchall()
