# -*- coding: utf-8 -*-
import inspect
import json
import pytest
from collections import OrderedDict, namedtuple
from decimal import Decimal
from enum import Enum, IntEnum

from intertwine.utils.tools import TEXT_TYPES

MyNamedTuple = namedtuple('MyNamedTuple', 'first second third')


class CrosswalkSignal(Enum):
    DONT_WALK = "Don't Walk"
    WALK = 'Walk'
    THREE = 3
    TWO = 2
    ONE = 1


TrafficSignal = IntEnum('TrafficSignal', 'RED YELLOW GREEN')


def type_annotated_fn(
        self,
        param_Dict,                     # type: Dict[Text: int]
        param_List=None,                # type: List[int]
        param_Set=None,                 # type: Set[int]
        param_Text=None,                # type: Text
        param_Tuple=None,               # type: Tuple[int, str, float]
        # Ignore this comment line
        param_bool=None,                # type: bool  # Ignore inline comment
        param_float=None,               # type: float
        param_int=None,                 # type: int
        param_str=None,                 # type: str
        param_unicode=None,             # type: unicode
        param_CrosswalkSignal=None,     # type: CrosswalkSignal
        param_TrafficSignal=None):      # type: TrafficSignal
        # type: (...) -> None  # Ignore return annotation
    """Type Annotated Function is just used for testing"""
    pass


@pytest.mark.unit
def test_derive_arg_types():
    """Test Derive Kwarg Types"""
    from intertwine.utils.tools import ANNOTATION_TYPE_MAP, derive_arg_types

    custom = (CrosswalkSignal, TrafficSignal)
    custom_map = {typ_.__name__: typ_ for typ_ in custom}

    arg_type_generator = derive_arg_types(type_annotated_fn, custom=custom)
    args = inspect.getfullargspec(type_annotated_fn).args

    start = 1 if args[0] in {'self', 'cls', 'meta'} else 0

    for i, (arg_name, arg_type) in enumerate(arg_type_generator, start=start):
        assert arg_name == args[i]
        arg_type_name = arg_name.split('_')[1]
        arg_type_check = ANNOTATION_TYPE_MAP.get(arg_type_name)
        if arg_type_check is None:
            arg_type_check = custom_map[arg_type_name]
        assert arg_type is arg_type_check


@pytest.mark.unit
@pytest.mark.parametrize('EnumType', (CrosswalkSignal, TrafficSignal))
def test_enumify(EnumType):
    """Test Enumify via Enum and IntEnum on name, value, int(value)"""
    from intertwine.utils.tools import enumify

    for signal in EnumType:
        assert enumify(EnumType, signal) is signal
        assert enumify(EnumType, signal.name) is signal
        assert enumify(EnumType, signal.value) is signal
        assert enumify(EnumType, str(signal.value)) is signal

    for value in ('Walk this Way', 'yellow', 0, 4, '2.0', '42'):
        with pytest.raises(ValueError) as e_info:
            enumify(EnumType, value)
        assert EnumType.__name__ in str(e_info)


@pytest.mark.unit
@pytest.mark.parametrize('limit', (-1, 3, 10))
def test_stringify(limit):
    from intertwine.utils.duck_typing import isiterable
    from intertwine.utils.tools import stringify
    from intertwine.utils.structures import PeekableIterator

    ord_a = ord('a')
    my_data_structure = OrderedDict(
        my_integer=42,
        my_float=3.14159,
        my_decimal=Decimal('2.718281828'),
        my_string='stringy',
        my_enum=TrafficSignal['RED'],
        my_named_tuple=MyNamedTuple('alpha', 'beta', 'gamma'),
        short_plain_tuple=('un', 'deux', 'trois'),
        long_plain_tuple=tuple((f'letter {chr(ord_a + i)}' for i in range(26))),
        short_ordered_dict=OrderedDict(a='apple', b='banana', c='cantaloupe'),
        long_ordered_dict=OrderedDict((f'key {chr(ord_a + i)}', f'value {i + 1}')
                                      for i in range(26)),
    )

    stringified = stringify(my_data_structure, limit)
    remaining = stringified
    items = PeekableIterator(my_data_structure.items())

    for key, value in items:
        start = remaining.find(key) + len(key) + 1
        if items.has_next():
            next_key, _ = items.peek()
            end = remaining.find(next_key)
        else:
            end = len(remaining)

        stringified_value = remaining[start:end]
        standardized_value = value._asdict() if hasattr(value, '_asdict') else value

        if hasattr(standardized_value, 'items'):
            for k, v in standardized_value.items():
                assert str(k) in stringified_value
                assert str(v) in stringified_value
        elif (isiterable(standardized_value) and
                not isinstance(standardized_value, TEXT_TYPES)):
            standardized_length = len(standardized_value)
            length = standardized_length if limit < 0 else min(limit, standardized_length)
            for i, v in enumerate(standardized_value):
                if i < length:
                    assert str(v) in stringified_value
                else:
                    assert str(v) not in stringified_value
        else:
            assert str(standardized_value) in stringified_value

        remaining = remaining[end:]


@pytest.mark.unit
@pytest.mark.parametrize("problem_name, org_name, geo_name, num_followers", [
    ('Homelessness', None, None, 100000),
    ('Homelessness', None, 'Austin', 10000),
    ('Sexual Assault', 'University of Texas', None, 10000),
    ('Sexual Assault', 'University of Texas', 'Austin', 5000),
    ('Homeless Often Lack ID', None, 'Travis County', 100),
    ('Lack of Standard Homeless Metrics', None, 'Greater Austin', 3),
    ('Homelessness', None, 'Lopeño', 0),
    ('Homelessness', None, 'Waxahachie', None),
])
def test_vardygrify(session, problem_name, org_name, geo_name, num_followers):
    """Test vardygrify by comparing vardygr and real communities"""
    from intertwine.communities.models import Community
    from intertwine.geos.models import Geo
    from intertwine.problems.models import Problem
    from intertwine.utils.vardygr import vardygrify

    problem = Problem(name=problem_name) if problem_name else None
    org = org_name if org_name else None
    geo = Geo(name=geo_name) if geo_name else None
    community_kwds = dict(problem=problem, org=org, geo=geo,
                          num_followers=num_followers)
    real_community = Community(**community_kwds)

    session.add(real_community)
    session.commit()

    vardygr_community = vardygrify(Community, **community_kwds)

    # Hide ids, since they will differ
    hide = Community.ID_FIELDS

    real_community_payload = real_community.jsonify(hide=hide)
    vardygr_community_payload = vardygr_community.jsonify(hide=hide)
    assert real_community_payload == vardygr_community_payload

    real_community_json = json.dumps(real_community_payload)
    vardygr_community_json = json.dumps(vardygr_community_payload)
    assert real_community_json == vardygr_community_json
