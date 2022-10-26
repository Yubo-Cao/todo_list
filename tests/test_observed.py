import pytest

from todo.data.observed import ObservedDict, ObservedDot, ObservedList, \
    observable, Notify, ALL


def test_observe_wrap():
    data = {}
    assert (parent := observable(data)) == ObservedDict({})
    assert observable([], parent).parent == parent


def test_observable_list():
    changes = []

    def callback(idx: Notify):
        changes.append(idx.index)

    ol = ObservedList([])
    ol.attach(callback)

    # because persistent storage is active, we need to clear the file

    def _assert_history(expected):
        assert changes == [expected]
        changes.clear()

    ol.append(1)
    _assert_history([0])
    ol.extend([2, 3])
    _assert_history([slice(1, 3, None)])
    ol.insert(0, 0)
    _assert_history([0])
    ol[0] = 4
    _assert_history([0])
    ol[1:3] = [5, 6]
    _assert_history([slice(1, 3)])
    ol.clear()
    _assert_history([ALL])
    assert ol == []
    _assert_history([ALL])
    assert len(ol) == 0
    _assert_history([ALL])
    assert repr(ol) == "ObservedList([])"
    _assert_history([ALL])
    assert str(ol) == "[]"
    _assert_history([ALL])


def test_observable_dict():
    dct = ObservedDict({"a": 1, "b": 2})
    changes = []

    def callback(notify: Notify):
        changes.append(notify.index)

    dct.attach(callback)
    dct["c"] = 3
    assert changes == [["c"]]
    del dct["a"]
    assert changes == [["c"], ["a"]]
    dct.update({
        "d": 4,
        "e": 5
    })
    try:
        assert changes == [["c"], ["a"], ["e", "d"]]  # order is not guaranteed
    except AssertionError:
        assert changes == [["c"], ["a"], ["d", "e"]]
    changes.clear()
    dct.clear()
    assert changes == [[ALL]]
    assert "a" not in dct


def test_attr_dct():
    dct = ObservedDict({"a": 1, "b": 2})
    changes = []

    def callback(notify: Notify):
        changes.append(notify.index)

    dct.attach(callback)
    dct.a = 3

    dct = ObservedDot(dct)
    with pytest.warns(UserWarning):
        dct.attach(callback)  # should warn about duplicate callback

    dct.a = 4
    assert changes == [["a"]]
    assert dct.a == 4
    assert dct["a"] == 4
    assert dct == {"a": 4, "b": 2}  # __eq__ is implemented

    with pytest.raises(AttributeError):
        dct.c


def test_nested():
    dct = ObservedDict({"a": 1, "b": {"c": 2}})
    dct = ObservedDot(dct)
    assert dct.b.c == 2
    assert type(dct) == ObservedDot
    assert dct.b.parent == dct
    dct.b.c = 3
    assert dct == {"a": 1, "b": {"c": 3}}
    dct.b = (1, [1, 2])
    assert dct == {"a": 1, "b": (1, [1, 2])}
    dct.b[1].append(3)
    assert dct == {"a": 1, "b": (1, [1, 2, 3])}
