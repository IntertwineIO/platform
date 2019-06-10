# -*- coding: utf-8 -*-
import random
from collections import OrderedDict, namedtuple
from random import choice

import pytest

from intertwine.utils.structures import InsertableOrderedDict, MultiKeyMap, Sentinel
from intertwine.utils.tools import nth_item


@pytest.mark.unit
def test_sentinel():
    """Test Sentinel via comparisons"""
    sentinel0 = Sentinel()
    same_sentinels = [sentinel0] * 3
    for sentinel in same_sentinels:
        assert sentinel is sentinel0

    unique_sentinels = [Sentinel() for _ in range(3)]
    for sentinel in unique_sentinels:
        assert sentinel is not sentinel0


def build_alphabet_map():
    ord_a = ord('a')
    return ((chr(ord_a+i), i+1) for i in range(26))


@pytest.mark.unit
def test_insertable_ordered_dict_init():
    """Test InsertableOrderedDict initialization"""
    # Initialize InsertableOrderedDict from iterable of 2-tuples
    iod0 = InsertableOrderedDict(build_alphabet_map())
    assert isinstance(iod0, InsertableOrderedDict)
    assert isinstance(iod0, OrderedDict)
    assert isinstance(iod0, dict)

    # Initialize InsertableOrderedDict from InsertableOrderedDict
    iod1 = InsertableOrderedDict(iod0)
    assert iod1 == iod0
    assert iod1 is not iod0

    # Initialize OrderedDict from InsertableOrderedDict
    od = OrderedDict(iod0)
    assert iod0 == od
    assert od == iod0
    assert not iod0 != od
    assert not od != iod0
    assert od is not iod0

    # Initialize InsertableOrderedDict from OrderedDict
    iod2 = InsertableOrderedDict(od)
    assert iod2 == iod0
    assert iod2 is not iod0

    # Initialize InsertableOrderedDict using copy()
    iod3 = iod0.copy()
    assert iod3 == iod0
    assert iod3 is not iod0

    # The repr evaluates to an identical InsertableOrderedDict
    iod4 = eval(repr(iod0))
    assert iod4 == iod0
    assert iod4 is not iod0


@pytest.mark.unit
def test_insertable_ordered_dict_insert():
    """Test InsertableOrderedDict via insertions"""
    iod0 = InsertableOrderedDict(build_alphabet_map())
    iod1 = iod0.copy()
    iod2 = iod0.copy()
    iod3 = iod0.copy()

    # Test insertion before/after an element in the middle
    assert nth_item(iod1, 8-1) == ('h', 8)
    assert nth_item(iod1, 9-1) == ('i', 9)
    iod1.insert('i', 'before_i', 8.5)
    assert nth_item(iod1, 8-1) == ('h', 8)
    assert nth_item(iod1, 9-1) == ('before_i', 8.5)
    assert nth_item(iod1, 10-1) == ('i', 9)
    assert len(iod1) == len(iod0) + 1
    iod1.insert('i', 'after_i', 9.5, after=True)
    assert nth_item(iod1, 10-1) == ('i', 9)
    assert nth_item(iod1, 11-1) == ('after_i', 9.5)
    assert nth_item(iod1, 12-1) == ('j', 10)
    assert len(iod1) == len(iod0) + 2

    # Test insertion before/after terminal elements
    assert nth_item(iod2, 1-1) == ('a', 1)
    assert nth_item(iod2, 26-1) == ('z', 26)
    iod2.insert('z', 'after_z', 26.5, after=True)
    assert nth_item(iod2, 26-1) == ('z', 26)
    assert nth_item(iod2, 27-1) == ('after_z', 26.5)
    assert len(iod2) == len(iod0) + 1
    iod2.insert('a', 'before_a', 0.5)
    assert nth_item(iod2, 1-1) == ('before_a', 0.5)
    assert nth_item(iod2, 2-1) == ('a', 1)
    assert len(iod2) == len(iod0) + 2

    # Test prepend/append
    iod3.append('after_z', 26.5)
    iod3.prepend('before_a', 0.5)
    assert iod3 == iod2


@pytest.mark.unit
def test_insertable_ordered_dict_set_and_get():
    """Test InsertableOrderedDict set and get"""
    iod0 = InsertableOrderedDict(build_alphabet_map())
    iod1 = InsertableOrderedDict()

    od = OrderedDict(build_alphabet_map())
    assert len(iod0) == len(od)

    for key, value in od.items():
        assert iod0[key] == value
        iod1[key] = value
        assert iod1.get(key) == value

    assert len(iod1) == len(od)


@pytest.mark.unit
def test_insertable_ordered_dict_delete():
    """Test InsertableOrderedDict delete"""
    iod0 = InsertableOrderedDict(build_alphabet_map())
    iod1 = iod0.copy()

    # Test deletion of last element
    assert nth_item(iod1, 25-1) == ('y', 25)
    assert nth_item(iod1, 26-1) == ('z', 26)
    del iod1['z']
    assert nth_item(iod1, 25-1) == ('y', 25)
    assert len(iod1) == len(iod0) - 1

    # Test deletion of element in middle
    assert nth_item(iod1, 9-1) == ('i', 9)
    assert nth_item(iod1, 10-1) == ('j', 10)
    assert nth_item(iod1, 11-1) == ('k', 11)
    del iod1['j']
    assert nth_item(iod1, 9-1) == ('i', 9)
    assert nth_item(iod1, 10-1) == ('k', 11)
    assert len(iod1) == len(iod0) - 2

    # Test deletion of first element
    assert nth_item(iod1, 1-1) == ('a', 1)
    assert nth_item(iod1, 2-1) == ('b', 2)
    del iod1['a']
    assert nth_item(iod1, 1-1) == ('b', 2)
    assert nth_item(iod1, 2-1) == ('c', 3)
    assert len(iod1) == len(iod0) - 3


@pytest.mark.unit
def test_insertable_ordered_dict_pop():
    """Test InsertableOrderedDict pop and popitem"""
    iod0 = InsertableOrderedDict(build_alphabet_map())
    iod1 = iod0.copy()

    # Test popitem of last item
    assert nth_item(iod1, 25-1) == ('y', 25)
    assert nth_item(iod1, 26-1) == ('z', 26)
    last_item = iod1.popitem()
    assert last_item == ('z', 26)
    assert nth_item(iod1, 25-1) == ('y', 25)
    assert len(iod1) == len(iod0) - 1

    # Test pop of item in the middle
    assert nth_item(iod1, 9-1) == ('i', 9)
    assert nth_item(iod1, 10-1) == ('j', 10)
    assert nth_item(iod1, 11-1) == ('k', 11)
    popped_value = iod1.pop('j')
    assert popped_value == 10
    assert nth_item(iod1, 9-1) == ('i', 9)
    assert nth_item(iod1, 10-1) == ('k', 11)
    assert len(iod1) == len(iod0) - 2

    # Test popitem of first item
    assert nth_item(iod1, 1-1) == ('a', 1)
    assert nth_item(iod1, 2-1) == ('b', 2)
    first_item = iod1.popitem(last=False)
    assert first_item == ('a', 1)
    assert nth_item(iod1, 1-1) == ('b', 2)
    assert nth_item(iod1, 2-1) == ('c', 3)
    assert len(iod1) == len(iod0) - 3


@pytest.mark.unit
def test_insertable_ordered_dict_iterables():
    """Test InsertableOrderedDict set and get"""
    iod = InsertableOrderedDict(build_alphabet_map())

    od = OrderedDict(build_alphabet_map())
    od_keys = list(od.keys())
    od_values = list(od.values())
    od_items = list(od.items())

    assert len(iod) == len(od)

    for i, key in enumerate(iod):
        assert key == od_keys[i]

    assert list(iod.keys()) == list(od_keys)
    for i, key in enumerate(iod.keys()):
        assert key == od_keys[i]

    assert list(iod.values()) == list(od_values)
    for i, value in enumerate(iod.values()):
        assert value == od_values[i]

    assert list(iod.items()) == list(od_items)
    for i, (key, value) in enumerate(iod.items()):
        assert key == od_keys[i]
        assert value == od_values[i]


@pytest.mark.unit
def test_insertable_ordered_dict_reversal():
    """Test InsertableOrderedDict reverse and reversed"""
    iod0 = InsertableOrderedDict(build_alphabet_map())
    iod1 = iod0.copy()
    iod1_items = list(iod1.items())

    # Test in-place reverse()
    iod1.reverse()
    iod1_items.reverse()
    assert iod1 != iod0
    assert list(iod1.items()) == iod1_items

    # Confirm double reversal equals the original
    iod1.reverse()
    iod1_items.reverse()
    assert iod1 == iod0
    assert list(iod1.items()) == iod1_items

    # Test reversed() iterator
    od = OrderedDict(iod0)
    assert list(reversed(iod0)) == list(reversed(od))
    assert list(reversed(iod0)) == list(reversed(list(iod0.keys())))
    assert list(reversed(list(reversed(iod0)))) == list(iod0.keys())


@pytest.mark.unit
def test_multi_key_map():
    """Test MultiKeyMap with a collection of namedtuples"""
    random.seed(42)

    fields = ('field1', 'field2', 'field3')
    ThingTuple = namedtuple('ThingTuple', fields)
    alphabet_size = 26
    ord_a = ord('a')
    things = [ThingTuple(i+1, chr(ord_a+i), 2*chr(ord_a+alphabet_size-1-i))
              for i in range(alphabet_size)]

    multi_key_map = MultiKeyMap(fields, things)

    for _ in range(10):
        thing = choice(things)
        field = choice(fields)
        key = getattr(thing, field)
        assert multi_key_map.get_by(field, key) == thing

    # things is sorted by field1, so first thing is first in map
    field1_map = multi_key_map.get_map_by('field1')
    assert next(iter(field1_map.keys())) == getattr(things[0], 'field1')
    # things is sorted by field2, so first thing is first in map
    field2_map = multi_key_map.get_map_by('field2')
    assert next(iter(field2_map.keys())) == getattr(things[0], 'field2')
    # things is reverse sorted by field3, so last thing is first in map
    field3_map = multi_key_map.get_map_by('field3')
    assert next(iter(field3_map.keys())) == getattr(things[-1], 'field3')
