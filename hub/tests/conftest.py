import pytest
from fake_ha import FakeHa


@pytest.fixture
async def fake_ha():
    ha = FakeHa()
    await ha.start()
    yield ha
    await ha.stop()
