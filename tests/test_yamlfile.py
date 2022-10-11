from pathlib import Path

from yaml import load, Loader

from todo.model.yamlfile import YamlFile

path = Path("tests/test.yaml")
path.unlink(missing_ok=True)
yaml = YamlFile(path, )


def test_load():
    assert yaml._data == {}


def test_save():
    yaml.test = "test"
    assert yaml._data == {"test": "test"}
    assert load(path.read_text(encoding='utf-8'), Loader=Loader) == {"test": "test"}


def test_nested():
    yaml.test = ["test", {"test": "target"}]
    assert yaml._data == {"test": ["test", {"test": "target"}]}
    assert load(path.read_text(encoding='utf-8'), Loader=Loader) == yaml._data
    assert yaml.test[1].test == "target"
    assert yaml.test[1]["test"] == "target"
    assert yaml.test[1]._data == {"test": "target"}


def test_iter():
    yaml.test = [{"a": "b"}, {"c": "d"}]
    for item in yaml.test:
        assert isinstance(item, YamlFile)


def test_fn():
    yaml.pop('test')
    assert yaml._data == {}
    t = yaml.setdefault('test', {})
    assert yaml._data == {'test': {}}
    assert t == {}
    t = yaml.setdefault('test', {'a': 'b'})
    assert yaml._data == {'test': {}}
    assert t == {}
    t.data = 'b'
    assert yaml._data == {'test': {'a': 'b'}}
    assert t == {'a': 'b'}
