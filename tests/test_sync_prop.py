import pytest

from todo.utils import *

def test_async():
    @sync
    async def async_func():
        return 1

    assert async_func() == 1

def test_sync():
    count = 0
    @sync_cached
    async def async_func():
        nonlocal count
        count += 1
        return count

    assert async_func() == 1
    assert async_func() == 1

def test_property():
    count = 0
    class Test:
        @sync_property
        async def prop(self):
            nonlocal count
            count += 1
            return 1

    assert Test().prop == 1
    assert Test().prop == 1
    assert count == 2

def test_property_refresh():
    count = 0
    class Test:
        @sync_property(cached=True)
        async def prop(self):
            nonlocal count
            count += 1
            return count

    test = Test()
    assert test.prop == 1
    test.__class__.prop.refresh(test)
    assert test.prop == 2
    test.prop = 4
    assert test.prop == 4

def test_property_set():
    class Test:
        @sync_property(cached=True, immutable=True)
        async def prop(self):
            return 1

    with pytest.raises(AttributeError):
        Test().prop = 2