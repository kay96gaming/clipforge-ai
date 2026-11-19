import logging, sys
from core.config import LOG_FILE
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
from database import db

if __name__ == "__main__":
    db.init()
    from ui.main_window import run
    run()
