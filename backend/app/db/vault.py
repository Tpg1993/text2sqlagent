import sqlite3
import uuid
import re
from app.config import settings

def _get_conn():
    conn = sqlite3.connect(settings.SQLITE_URL.replace("sqlite:///", ""))
    conn.row_factory = sqlite3.Row
    return conn

def init_vault():
    """Ensure the PII vault table exists."""
    with _get_conn() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pii_vault (
                token TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                original_value TEXT NOT NULL
            )
        ''')
        conn.commit()

def store_pii(entity_type: str, original_value: str) -> str:
    """
    Stores the original PII value and returns a secure token.
    Uses first 8 chars of a UUID for uniqueness while keeping it readable.
    """
    with _get_conn() as conn:
        # Check if we already have this exact value stored to avoid duplicates
        cursor = conn.cursor()
        cursor.execute("SELECT token FROM pii_vault WHERE entity_type = ? AND original_value = ?", (entity_type, original_value))
        row = cursor.fetchone()
        if row:
            return row['token']

        # Generate new token
        unique_id = uuid.uuid4().hex[:8]
        token = f"[PII_{entity_type}_{unique_id}]"
        
        conn.execute(
            "INSERT INTO pii_vault (token, entity_type, original_value) VALUES (?, ?, ?)",
            (token, entity_type, original_value)
        )
        conn.commit()
    
    return token

def retrieve_pii(token: str) -> str:
    """
    Retrieves the original PII value from a token.
    Returns the token itself if not found in the vault.
    """
    with _get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT original_value FROM pii_vault WHERE token = ?", (token,))
        row = cursor.fetchone()
        if row:
            return row['original_value']
    
    return token

def deanonymize_text(text: str) -> str:
    """
    Scans text for tokens (e.g. <EMAIL_ADDRESS_xxxxxxxx>) and replaces them 
    with their original values from the vault.
    """
    if not text:
        return text
        
    # 1. First, replace any OLD PII tokens that use <TAGS> (e.g. <EMAIL_ADDRESS>) 
    # with bracket notation [EMAIL_ADDRESS] so they don't get swallowed by UI HTML parsers
    # in case they are retrieved from an old document embedded in FAISS.
    text = re.sub(r'<([A-Z_]+)>', r'[\1]', text)
    
    # 2. Find new active tokens looking like [PII_ENTITY_TYPE_xxxxxxxx]
    # Note: entity types can have underscores, and hex ID is 8 chars
    pattern = r'\[PII_([A-Z_]+_[a-f0-9]{8})\]'
    
    def replacer(match):
        token = f"[PII_{match.group(1)}]"
        return retrieve_pii(token)
        
    return re.sub(pattern, replacer, text)

# Initialize the table when module is loaded
init_vault()
