import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class DatabaseSchemaTests(unittest.TestCase):
    def test_initial_migration_creates_all_master_plan_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "relatpy.db"
            config = Config(str(BACKEND_ROOT / "alembic.ini"))
            config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

            command.upgrade(config, "head")

            engine = create_engine(f"sqlite:///{db_path}")
            try:
                tables = set(inspect(engine).get_table_names())
            finally:
                engine.dispose()

            self.assertTrue(
                {
                    "automations",
                    "automation_versions",
                    "destinations",
                    "executions",
                    "execution_automations",
                    "events",
                    "artifacts",
                    "checkpoints",
                }.issubset(tables)
            )

    def test_sqlite_foreign_keys_are_enabled(self):
        from app.database import create_engine_for_url

        engine = create_engine_for_url("sqlite:///:memory:")
        with engine.connect() as connection:
            enabled = connection.execute(text("PRAGMA foreign_keys")).scalar_one()

        self.assertEqual(enabled, 1)


if __name__ == "__main__":
    unittest.main()
