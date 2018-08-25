from collections import MutableMapping, KeysView, ItemsView, ValuesView

import pytest

from msl.io.metadata import Metadata


def test_behaves_like_dict():

    meta = Metadata(is_read_only=False, vertex_name='', x=1)
    assert isinstance(meta, MutableMapping)
    assert len(meta) == 1
    assert meta['x'] == 1
    assert meta.get('x') == 1
    assert meta.get('y', -99) == -99
    assert 'x' in meta
    assert 'y' not in meta
    assert repr(meta) == repr({'x': 1})
    assert str(meta).startswith('<Metadata')

    # test copy()
    cp = meta.copy()
    assert isinstance(cp, Metadata)
    assert id(cp) != id(meta)
    assert not cp.is_read_only
    assert cp._vertex_name == meta._vertex_name
    assert cp['x'] == 1
    cp['x'] = 2
    assert cp['x'] == 2
    assert meta['x'] == 1
    assert len(cp) == 1

    # test fromkeys, with default=None, and del
    d = meta.fromkeys({'a', 'b', 'c'})
    assert isinstance(d, Metadata)
    assert id(d) != id(meta)
    assert not d.is_read_only
    assert len(d) == 3
    assert d['a'] is None
    assert d['b'] is None
    assert d['c'] is None
    del d['a']
    assert 'a' not in meta
    with pytest.raises(KeyError):
        _ = d['a']
    del d['c']
    with pytest.raises(KeyError):
        _ = d['c']
    with pytest.raises(AttributeError):
        del d.c
    assert len(d) == 1

    # test fromkeys(), with default != None, and clear()
    d = meta.fromkeys({'a', 'b', 'c', 'd'}, value='foo')
    assert isinstance(d, Metadata)
    assert id(d) != id(meta)
    assert not d.is_read_only
    assert len(d) == 4
    assert d['a'] == 'foo'
    assert d['b'] == 'foo'
    assert d['c'] == 'foo'
    assert d['d'] == 'foo'
    assert 'a' not in meta
    d.clear()
    assert len(d) == 0

    # test pop()
    assert 'x' in meta
    assert meta.pop('x') == 1
    assert 'x' not in meta
    with pytest.raises(KeyError):
        meta.pop('x')
    assert meta.pop('x', 22) == 22

    # test popitem()
    assert len(meta) == 0
    meta['x'] = 1
    assert len(meta) == 1
    key, value = meta.popitem()
    assert key == 'x'
    assert value == 1
    assert len(meta) == 0

    # test setdefault()
    assert 'foo' not in meta
    meta.setdefault('xxx')
    assert meta['xxx'] is None
    meta.setdefault('foo', 'bar')
    assert meta['foo'] == 'bar'

    # test update()
    assert len(meta) == 2
    meta.update(dict(a=1, b=2, c=3, hello='world!'))
    assert len(meta) == 6
    assert meta['xxx'] is None
    assert meta['foo'] == 'bar'
    assert meta['a'] == 1
    assert meta['b'] == 2
    assert meta['c'] == 3
    assert meta['hello'] == 'world!'

    expected_keys = ['xxx', 'foo', 'a', 'b', 'c', 'hello']
    expected_values = [None, 'bar', 1, 2, 3, 'world!']

    # test items()
    items = meta.items()
    assert isinstance(items, ItemsView)
    keys = [k for k in expected_keys]
    values = [v for v in expected_values]
    count = 0
    for key, value in items:
        assert key in keys
        keys.pop(keys.index(key))
        assert value in values
        values.pop(values.index(value))
        count += 1
    assert count == 6

    # test keys()
    keys = meta.keys()
    assert isinstance(keys, KeysView)
    keys_ = [k for k in expected_keys]
    count = 0
    for key in keys:
        assert key in keys_
        keys_.pop(keys_.index(key))
        count += 1
    assert count == 6

    # test values()
    values = meta.values()
    assert isinstance(values, ValuesView)
    values_ = [v for v in expected_values]
    count = 0
    for value in values:
        assert value in values_
        values_.pop(values_.index(value))
        count += 1
    assert count == 6

    # test iter()
    count = 0
    keys_ = [k for k in expected_keys]
    for key in iter(meta):
        assert isinstance(key, str)
        assert key in keys_
        keys_.pop(keys_.index(key))
        count += 1
    assert count == 6


def test_attribute_access():

    meta = Metadata(is_read_only=True, vertex_name='', x=1, FOO='BaR')
    assert meta['x'] == 1
    assert meta.x == 1
    assert meta['FOO'] == 'BaR'
    assert meta.FOO == 'BaR'

    with pytest.raises(AttributeError):
        _ = meta.something

    with pytest.raises(KeyError):
        _ = meta['something']


def test_nested_dict_as_value():
    meta = Metadata(is_read_only=True, vertex_name='', none=None, nested={'dict1': {'dict2': {'dict3': (1, 2, 3)}}})
    assert meta['none'] is None
    assert meta.none is None
    assert meta['nested']['dict1']['dict2']['dict3'] == (1, 2, 3)
    assert meta.nested.dict1.dict2.dict3 == (1, 2, 3)
    assert meta.nested['dict1'].dict2['dict3'] == (1, 2, 3)

    with pytest.raises(AttributeError):
        _ = meta.none.is_read_only  # meta.none is not a Metadata object
    with pytest.raises(AttributeError):
        _ = meta['none'].is_read_only  # meta['none'] is not a Metadata object

    # test that all Metadata objects have the same read-only mode
    assert meta.is_read_only
    assert meta.nested.is_read_only
    assert meta.nested.dict1.is_read_only
    assert meta.nested.dict1.dict2.is_read_only

    # test read-only mode propagates
    meta.is_read_only = False
    assert not meta.is_read_only
    assert not meta.nested.is_read_only
    assert not meta.nested.dict1.is_read_only
    assert not meta.nested.dict1.dict2.is_read_only


def test_read_only():

    meta = Metadata(is_read_only=True, vertex_name='', foo='bar')
    assert meta.is_read_only

    # cannot modify an existing value (key access)
    with pytest.raises(ValueError):
        meta['foo'] = 1

    # cannot modify an existing value (attrib access)
    with pytest.raises(ValueError):
        meta.foo = 1

    # cannot delete a key (key access)
    with pytest.raises(ValueError):
        del meta['foo']

    # cannot delete a key (attrib access)
    with pytest.raises(ValueError):
        del meta.foo

    # cannot create a new key-value pair (key access)
    with pytest.raises(ValueError):
        meta['anything'] = -1

    # cannot create a new key-value pair (attrib access)
    with pytest.raises(ValueError):
        meta.anything = -1

    # cannot do an update()
    with pytest.raises(ValueError):
        meta.update({'whatever': 1.234})

    # cannot do a pop()
    with pytest.raises(ValueError):
        meta.pop('foo')

    # cannot do a popitem()
    with pytest.raises(ValueError):
        meta.popitem()

    # cannot do a setdefault(), default value
    with pytest.raises(ValueError):
        meta.setdefault('new_key')

    # cannot do a setdefault(), custom value
    with pytest.raises(ValueError):
        meta.setdefault('new_key', 'new_value')

    # cannot do a clear()
    with pytest.raises(ValueError):
        meta.clear()

    # make sure that meta has the expected data
    assert len(meta) == 1
    assert meta['foo'] == 'bar'

    # make it writeable
    meta.is_read_only = False
    assert not meta.is_read_only

    # can modify an existing value (key access)
    meta['foo'] = 1

    # can modify an existing value (attrib access)
    assert meta.foo == 1
    meta.foo = 2

    # can create a new key-value pair (key access)
    meta['negative'] = -1

    # can create a new key-value pair (attrib access)
    meta.one_thousand = 1000

    # can do an update()
    meta.update({'whatever': 1.234})

    # can do a setdefault(), default value
    meta.setdefault('none_value')

    # can do a setdefault(), custom value
    meta.setdefault('custom', 'new_value')

    # make sure that meta has the expected data
    assert len(meta) == 6
    assert meta['foo'] == 2
    assert meta.negative == -1
    assert meta['one_thousand'] == 1000
    assert meta.whatever == 1.234
    assert meta['none_value'] is None
    assert meta.custom == 'new_value'

    # can delete a key (key access)
    del meta['foo']
    del meta['custom']

    # can delete a key (attrib access)
    del meta.one_thousand
    del meta.none_value

    # can do a pop()
    value = meta.pop('negative')
    assert value == -1

    # can do a popitem()
    assert len(meta) == 1
    key, value = meta.popitem()
    assert key == 'whatever'
    assert value == 1.234

    # can do a clear()
    meta.update({'a': 'hello', 'b': 'world'})
    assert len(meta) == 2
    meta.clear()
    assert len(meta) == 0

    # make it read only again
    meta.is_read_only = True
    assert meta.is_read_only

    # cannot create a new key-value pair (key access)
    with pytest.raises(ValueError):
        meta['anything'] = -1

    # cannot create a new key-value pair (attrib access)
    with pytest.raises(ValueError):
        meta.anything = -1
