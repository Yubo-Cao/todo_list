from todo.utils import ClassInstanceDispatch


def test_dispatch():
    class Test:
        @ClassInstanceDispatch.dispatch
        def test(self):
            pass

        @test.register
        def test_class(cls):
            return "class"

        @test.register(kind="instance")
        def test_instance(self):
            return "instance"

    assert Test.test() == "class"
    assert Test().test() == "instance"


def test_decorator():
    history = []

    class Test:
        def __init__(self, value):
            self.value = value

        @ClassInstanceDispatch.decorator_dispatch(name="test")
        def test(self, fn):
            def deco(slf, *args, **kwargs):
                history.append(slf.value)
                history.append(result := fn(slf, *args, **kwargs))
                return result

            return deco

    class Client:
        def __init__(self, test):
            self.test = test

        @Test.test
        def test(self, value):
            return value

    client = Client(Test("test"))
    assert client.test("value") == "value"
    assert history == ["test", "value"]


def test_decorator():
    history = []

    class Test:
        def __init__(self, value):
            self.value = value

        @ClassInstanceDispatch.decorator_dispatch(name="test")
        def test(self, fn):
            def deco(slf, *args, **kwargs):
                history.append(self.value)
                history.append(result := fn(slf, *args, **kwargs))
                return result

            return deco

    class Client:
        def __init__(self, test):
            self.test = test

        @Test.test
        def test_fn(self, value):
            return value

    client = Client(Test("test"))
    assert client.test_fn("value") == "value"
    assert history == ["test", "value"]
