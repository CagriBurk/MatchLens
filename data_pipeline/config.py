from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
TRANSFERMARKT_DIR = RAW_DIR / "transfermarkt"
ESPN_RAW_DIR = RAW_DIR / "espn"
DATABASE_DIR = PROJECT_ROOT / "database"
DB_PATH = DATABASE_DIR / "matchlens.db"
