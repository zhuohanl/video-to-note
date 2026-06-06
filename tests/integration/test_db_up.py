import os
import subprocess

import psycopg


def _select_one_via_compose_container() -> None:
    result = subprocess.run(
        [
            "docker",
            "exec",
            "vtn-postgres",
            "psql",
            "-U",
            "vtn",
            "-d",
            "vtn",
            "-tAc",
            "SELECT 1",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.stdout.strip() == "1"


def test_postgres_accepts_select_one() -> None:
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                assert cursor.fetchone() == (1,)
    else:
        _select_one_via_compose_container()
