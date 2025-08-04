PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT CHECK(role IN ('ospite', 'user', 'admin', 'superadmin')) NOT NULL,
    reparto TEXT,
    azienda TEXT,
    attivo INTEGER DEFAULT 1
);
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    uploaded_by INTEGER,
    reparto TEXT,
    azienda TEXT,
    is_shared INTEGER DEFAULT 0,
    is_protected INTEGER DEFAULT 0,
    is_downloadable INTEGER DEFAULT 1,
    password TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(uploaded_by) REFERENCES users(id) );
CREATE TABLE permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    user_email TEXT,
    expiry_date DATETIME,
    can_view INTEGER DEFAULT 1,
    can_download INTEGER DEFAULT 0,
    FOREIGN KEY(document_id) REFERENCES documents(id) );
CREATE TABLE access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    document_id INTEGER,
    action TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(document_id) REFERENCES documents(id) );
DELETE FROM sqlite_sequence;
COMMIT;
