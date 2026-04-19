from autonomy.db import AutonomyDB


def test_autonomy_db_creates_expected_tables(tmp_path):
    db = AutonomyDB(tmp_path / 'autonomy.db')
    tables = {
        row['name']
        for row in db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
    }
    expected = {
        'goals',
        'policies',
        'signals',
        'world_state',
        'opportunities',
        'executions',
        'reviews',
        'learnings',
    }
    assert expected.issubset(tables)
    db.close()
