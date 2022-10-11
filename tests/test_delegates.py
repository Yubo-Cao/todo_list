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

    @delegate(target=A, name="a")
    class B:
        def __init__(self, a):
            self.a = a

    data = [1, 2, 3]
    b = B(A(data))
    assert len(b) == 3
    assert b() == data
    assert b.normal() == data
