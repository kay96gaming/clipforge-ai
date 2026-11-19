"""SQLite project storage. Deleting a project never touches the user's video files."""
import json, sqlite3, time
from core.config import APP_DIR

DB_PATH = APP_DIR / "clipforge.db"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c


def init():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY, name TEXT, source TEXT,
            settings TEXT, transcript TEXT, status TEXT DEFAULT 'new', created REAL);
        CREATE TABLE IF NOT EXISTS clips(id INTEGER PRIMARY KEY, project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
            idx INTEGER, start REAL, end REAL, title TEXT, hook TEXT, text TEXT, score REAL, reason TEXT,
            description TEXT, hashtags TEXT, exported_path TEXT);
        CREATE TABLE IF NOT EXISTS exports(id INTEGER PRIMARY KEY, project_id INTEGER, path TEXT, created REAL);
        """)


def create_project(name, source, settings) -> int:
    with _conn() as c:
        return c.execute("INSERT INTO projects(name,source,settings,created) VALUES(?,?,?,?)",
                         (name, source, json.dumps(settings), time.time())).lastrowid


def get_project(pid):
    with _conn() as c:
        r = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    return dict(r) if r else None


def list_projects():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT id,name,source,status,created FROM projects ORDER BY created DESC")]


def rename_project(pid, name):
    with _conn() as c:
        c.execute("UPDATE projects SET name=? WHERE id=?", (name, pid))


def delete_project(pid):
    with _conn() as c:
        c.execute("DELETE FROM projects WHERE id=?", (pid,))


def save_transcript(pid, words):
    with _conn() as c:
        c.execute("UPDATE projects SET transcript=?, status='transcribed' WHERE id=?", (json.dumps(words), pid))


def load_transcript(pid):
    with _conn() as c:
        r = c.execute("SELECT transcript FROM projects WHERE id=?", (pid,)).fetchone()
    return json.loads(r["transcript"]) if r and r["transcript"] else None


def save_clips(pid, clips):
    with _conn() as c:
        c.execute("DELETE FROM clips WHERE project_id=?", (pid,))
        for i, k in enumerate(clips, 1):
            c.execute("INSERT INTO clips(project_id,idx,start,end,title,hook,text,score,reason,description,hashtags) "
                      "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      (pid, i, k["start"], k["end"], k["title"], k["hook"], k["text"], k["score"], k["reason"],
                       k.get("description", ""), " ".join(k.get("hashtags", []))))
        c.execute("UPDATE projects SET status='clips_ready' WHERE id=?", (pid,))


def load_clips(pid):
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM clips WHERE project_id=? ORDER BY idx", (pid,))]


def record_export(pid, path):
    with _conn() as c:
        c.execute("INSERT INTO exports(project_id,path,created) VALUES(?,?,?)", (pid, path, time.time()))
