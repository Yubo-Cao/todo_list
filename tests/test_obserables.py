from typing import Optional

import pytest

from todo.model.observables import ObservableDict, AttributeObservable, ObservableCollection, ObservableList, observable


def test_observe_wrap():
    data = {}
    assert (parent := observable(data)) == ObservableDict({})
    assert observable([], parent).parent == parent

def test_observable_list():
    changes = []

    def callback(idx: tuple[list[int], Optional[ObservableCollection]]):
        changes.append(idx[0])

    ol = ObservableList([])
    ol.attach(callback)
    # because persistent storage is active, we need to clear the file

    ol.append(1)
    assert changes == [[0]]
    ol.append(2)
    assert changes == [[0], [1]]
    ol.extend([3, 4])
    assert changes == [[0], [1], [2, 3]]
    ol.reverse()
    assert changes == [[0], [1], [2, 3], [0, 1, 2, 3]]
    ol.remove(3)
    assert changes == [[0], [1], [2, 3], [0, 1, 2, 3], [1]]
    ol.pop(0)
    assert changes == [[0], [1], [2, 3], [0, 1, 2, 3], [1], [0]]
    ol[0] = 5
    assert changes == [[0], [1], [2, 3], [0, 1, 2, 3], [1], [0], [0]]
    ol[1] = 6
    assert changes == [[0], [1], [2, 3], [0, 1, 2, 3], [1], [0], [0], [1]]
    assert len(ol) == 2


def test_observable_list_methods():
    changes = []

    def callback(idx: tuple[list[int], Optional[ObservableCollection]]):
        changes.append(idx[0])

    l1 = ObservableList([1, 2, 3])
    l2 = ObservableList([3, 2, 1])
    l1.attach(callback)
    l2.attach(callback)

    l1.extend(l2)
    assert changes == [[3, 4, 5]]
    l1.reverse()
    assert changes == [[3, 4, 5], [0, 1, 2, 3, 4, 5]]
    l1.sort()
    assert changes == [[3, 4, 5], [0, 1, 2, 3, 4, 5], [0, 1, 2, 3, 4, 5]]


def test_observable_dict():
    dct = ObservableDict({"a": 1, "b": 2})
    changes = []

    def callback(idx: tuple[list[int], Optional[ObservableCollection]]):
        [1] is None
        changes.append(idx[0])

    dct.attach(callback)
    dct["c"] = 3
    assert changes == [["c"]]
    del dct["a"]
    assert changes == [["c"], ["a"]]
    dct.update({
        "d": 4,
        "e": 5
    })
    assert changes == [["c"], ["a"], ["d", "e"]]
    changes.clear()
    dct.clear()
    assert changes == [["b", "c", "d", "e"]]
    assert "a" not in dct


def test_attr_dct():
    dct = ObservableDict({"a": 1, "b": 2})
    changes = []

    def callback(idx: tuple[list[int], Optional[ObservableCollection]]):
        changes.append(idx[0])

    dct.attach(callback)
    dct.a = 3

    dct = AttributeObservable(dct)
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
    dct = ObservableDict({"a": 1, "b": {"c": 2}})
    changes = []

    def callback(idx: tuple[list[int], Optional[ObservableCollection]]):
        changes.append(idx)

    dct.attach(callback)
    dct = AttributeObservable(dct)
    assert dct.b.c == 2
    assert type(dct) == AttributeObservable
    assert dct.b.parent == dct
    dct.b.c = 3
    assert changes == [(["c"], dct.b)]

    changes.clear()
    dct.b = (1, [1, 2])
    assert changes == [(["b"], dct)]
    changes.clear()
    dct.b[1].append(3)
    assert changes == [([2], dct.b[1])]
