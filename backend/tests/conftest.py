import pytest

from scripts.seed import run_seed


@pytest.fixture(autouse=True)
def seed_db_before_each_test():
    """Réinitialise la base à l'état seedé avant chaque test.

    Garantit l'isolation : un test qui modifie la base (ex. PUT) ne
    contamine pas les tests suivants.
    """
    run_seed()
    yield
