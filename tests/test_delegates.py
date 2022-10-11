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
