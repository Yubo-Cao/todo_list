import pytest
from todo.integrations.spider import SessionManager


@pytest.mark.asyncio
async def test_session_manager():
    class Test:
        def __init__(self):
            self.manager = SessionManager()
            self.test_instance = self.manager.supply(self.test_instance)

        @SessionManager.supply
        async def test(self, session):
            async with session.get("https://www.google.com") as resp:
                assert resp.ok

        async def test_instance(self, session):
            async with session.get("https://www.google.com") as resp:
                assert resp.ok

    test = Test()
    await test.test_instance()
    await test.test()
    await test.manager.close()
