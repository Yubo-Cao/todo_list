from pathlib import Path

from yaml import load, Loader

from todo.model import AttributeObservable, YamlFileObserver

path = Path("tests/test.yaml")
path.unlink(missing_ok=True)
file_observer = YamlFileObserver({}, path)
yaml = AttributeObservable(file_observer.to_observable())


def test_load():
    assert yaml == {}
    obs = file_observer.to_observable()
    obs2 = file_observer.to_observable()
    assert obs is obs2


def test_dump():
    yaml.test = "test"
    assert yaml == {"test": "test"}
    assert load(path.read_text(encoding='utf-8'), Loader=Loader) == {"test": "test"}
    assert file_observer.load() == {"test": "test"}


def test_nested():
    yaml.test = ["test", {"test": "target"}]
    assert yaml == {"test": ["test", {"test": "target"}]}
    assert yaml.test[1].test == "target"
    assert yaml.test[1]["test"] == "target"
    assert yaml.test[1] == {"test": "target"}


def test_iter():
    yaml.test = [{"a": "b"}, {"c": "d"}]
    for item in yaml.test:
        assert isinstance(item, AttributeObservable)


def test_fn():
    yaml.pop('test')
    assert yaml == {}
    t = yaml.setdefault('test', {})
    assert yaml == {'test': {}}
    assert t == {}
    assert t.parent is yaml

    t = yaml.setdefault('test', {'a': 'b'})
    assert yaml == {'test': {}}
    assert t == {}
    t.data = 'b'
    assert yaml == {'test': {'data': 'b'}}
    assert t == {'data': 'b'}
