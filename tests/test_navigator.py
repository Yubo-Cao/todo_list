from yarl import URL

from todo.integrations.spider import Navigator


def test_init():
    navigator = Navigator("root", "https://example.com")
    assert navigator.root == navigator
    assert navigator.name == "root"
    assert navigator.url == URL("https://example.com")


def test_init_with_parent():
    parent = Navigator("parent", "https://example.com")
    navigator = Navigator("child", "https://example.com", parent=parent)
    assert navigator.root == parent
    assert navigator.name == "child"
    assert navigator.url == URL("https://example.com")


def test_attribute():
    parent = Navigator("parent", "https://example.com")
    parent.child = "https://example.com"
    assert parent.child.name == "child"
    assert parent.child.url == URL("https://example.com")
    assert len(parent) == 1
    assert parent.child in parent


data = {
    "root": "https://example.com",
    "children": [
        {
            "child1": "https://example.com",
        },
        {
            "child2": "https://example.com",
        },
    ],
}


def test_load():
    navigator = Navigator.load(data)
    assert navigator.root == navigator
    assert navigator.name == "root"
    assert navigator.url == URL("https://example.com")
    assert navigator.child1.name == "child1"
    assert navigator.child1.url == URL("https://example.com")
    assert navigator.child2.name == "child2"
    assert navigator.child2.url == URL("https://example.com")
    assert len(navigator) == 2


def test_dump():
    navigator = Navigator.load(data)
    assert navigator.dump() == data


def test_find():
    nav = Navigator("root", "https://example.com")
    nav.c1 = "https://child1.com"
    nav.c2 = "https://child2.com"
    nav.c1.c11 = "https://child11.com"

    assert len(nav) == 2
    assert nav.find("c1").name == "c1"
    assert nav.find("c1").url == URL("https://child1.com")
    assert nav.find("c2").name == "c2"
