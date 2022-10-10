from todo.model import ObservableList


def test_observable_list():
    changes = []

    def callback(idx):
        changes.append(idx)

    ol = ObservableList("tests/observable_list.yaml", on_change_callbacks=[callback])
    # because persistent storage is active, we need to clear the file
    ol.clear()
    changes.clear()

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