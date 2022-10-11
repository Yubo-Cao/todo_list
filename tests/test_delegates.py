from todo.utils import delegate


def test_delegate():
    class A:
        def __init__(self, data):
            self.data = data

        def __call__(self, *args, **kwargs):
            return self.data

        def __len__(self):
            return len(self.data)

        def normal(self):
            return self.data

    class C:
        def __call__(self, *args, **kwargs):
            return 1

        def __len__(self):
            return 1

        def normal(self):
            return "C"

    @delegate(target=A, instance_name="a")
    class B:
        def __init__(self, a):
            self.a = a

    data = [1, 2, 3]
    b = B(A(data))
    assert len(b) == 3
    assert b() == data
    assert b.normal() == data
    # allow late binding
    b.a = C()
    assert len(b) == 1
    assert b() == 1
    assert b.normal() == "C"


def test_delegates_no_target():
    class A:
        def __init__(self, data):
            self.data = data

        def __call__(self, *args, **kwargs):
            return self.data

        def __len__(self):
            return len(self.data)

        def normal(self):
            return self.data

    @delegate(instance_name="a", suppress_log=True)
    class B:
        def __init__(self, a):
            self.a = a

    data = [1, 2, 3]
    b = B(A(data))
    assert len(b) == 3
    assert b() == data
    assert b.normal() == data


def test_setattr():
    class A: pass

    @delegate(target=A, instance_name="a", enable_setattr=True)
    class B:
        def __init__(self, a):
            self.a = a

    data = [1, 2, 3]
    b = B(a := A())
    b.c = 1
    assert b.c == 1
    assert a.c == 1


def test_getattr():
    class A:
        def __getattr__(self, item):
            if item == "c":
                return 1
            raise AttributeError

    @delegate(instance_name="a", suppress_log=True)
    class B:
        def __init__(self, a):
            self.a = a

        def __getattr__(self, item):
            if item == "d":
                return 2
            raise AttributeError

    data = [1, 2, 3]
    b = B(a := A())
    assert b.c == 1
    assert a.c == 1
    assert b.d == 2
