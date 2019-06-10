# -*- coding: utf-8 -*-
from decimal import Decimal

import pytest

from intertwine.utils.quantized import QuantizedDecimal

ABS = 'abs(a)'
COMPLEX = 'complex(a)'
DIVMOD = 'divmod(a, b)'
FLOAT = 'float(a)'
INT = 'int(a)'
POW = 'pow(a, b)'


@pytest.mark.unit
@pytest.mark.parametrize('number', [
    str('3.14159265359'),
    float(3.14159265359),
    98765432109876543210,
    42,
])
@pytest.mark.parametrize('precision', [None, 0, 1, 7])
def test_quantized_decimal_core_interactions(number, precision):
    """Test core quantized decimal interactions"""
    prec = (QuantizedDecimal.DEFAULT_PRECISION if precision is None
            else precision)
    mult = Decimal(10) ** prec
    quant = 1 / mult
    dec_value = Decimal(number).quantize(quant)
    int_value = int(dec_value * mult)

    qd = QuantizedDecimal(number, precision)

    assert qd.precision == prec
    assert qd.value == dec_value
    assert eval(repr(qd)) == qd

    dequantized = qd.dequantize()
    assert dequantized == int_value
    assert QuantizedDecimal.requantize(dequantized, precision) == qd
    assert QuantizedDecimal(dequantized, precision, requantize=True) == qd

    assert QuantizedDecimal.quantize(number, precision) == dec_value
    assert QuantizedDecimal.cast(number, precision) == qd
    assert QuantizedDecimal.cast(qd, precision) is qd

    prec1 = prec + 1
    quant1 = 1 / (Decimal(10) ** Decimal(prec1))
    dec_value1 = QuantizedDecimal.quantize(qd, precision=prec1)
    assert dec_value1 == dec_value.quantize(quant1)


@pytest.mark.unit
@pytest.mark.parametrize(('number1', 'number2'), [
    ('2.718281828', '3.14159265359'),
])
@pytest.mark.parametrize('precision', [5])
def test_quantized_decimal_comparisons(precision, number1, number2):
    """Test quantized decimal comparisons"""
    qd1 = QuantizedDecimal(number1, precision)
    qd2 = QuantizedDecimal(number2, precision)

    qd1_copy = QuantizedDecimal(qd1, precision)

    assert qd1 == qd1_copy
    assert qd1 == qd1_copy.value
    assert qd1.value == qd1_copy

    assert qd1 != qd2
    assert qd1 != qd2.value
    assert qd1.value != qd2

    assert qd1 < qd2
    assert qd1 < qd2.value
    assert qd1.value < qd2

    assert qd1 <= qd2
    assert qd1 <= qd2.value
    assert qd1.value <= qd2
    assert qd1 <= qd1_copy
    assert qd1 <= qd1_copy.value
    assert qd1.value <= qd1_copy

    assert qd2 > qd1
    assert qd2 > qd1.value
    assert qd2.value > qd1

    assert qd2 >= qd1
    assert qd2 >= qd1.value
    assert qd2.value >= qd1
    assert qd1 >= qd1_copy
    assert qd1 >= qd1_copy.value
    assert qd1.value >= qd1_copy


def stringify_operation(operator, *operands):
    left_paren_index = operator.find('(')
    if left_paren_index == -1:
        if len(operands) == 1:
            return operator + operands[0]
        return ' {} '.format(operator).join(operands[:2])

    params = operator[left_paren_index:].strip('() ').split(',')
    fn = operator[:left_paren_index].strip()
    args = ', '.join(operands[:len(params)])
    return '{fn}({args})'.format(fn=fn, args=args)


@pytest.mark.unit
@pytest.mark.parametrize('operator',
                         ['+', '-', '*', '/', '//', '%', '**', POW, DIVMOD])
@pytest.mark.parametrize(('number1', 'number2'),
                         [('34.21138532110', '1.01234567890')])
@pytest.mark.parametrize('precision', [11])
def test_quantized_decimal_binary_math(operator, number1, number2, precision):
    """Test quantized decimal binary operations, including in-place"""
    qd1 = QuantizedDecimal(number1, precision)
    qd2 = QuantizedDecimal(number2, precision)
    assert qd1 == qd1.value and qd2 == qd2.value

    # Test left-variant where left/right are both QuantizedDecimal
    qd3 = eval(stringify_operation(operator, 'qd1', 'qd2'))
    qd3_value = eval(stringify_operation(operator, 'qd1.value', 'qd2.value'))

    if operator != DIVMOD:
        assert isinstance(qd3, QuantizedDecimal)
        quant = 1 / (Decimal(10) ** Decimal(precision))
        qd3_value = qd3_value.quantize(quant)
    assert qd3 == qd3_value
    # Test left-variant where right side is Decimal
    qd3a = eval(stringify_operation(operator, 'qd1', 'qd2.value'))
    if operator != DIVMOD:
        assert isinstance(qd3a, QuantizedDecimal)
    assert qd3a == qd3
    # Test right-variant where left side is Decimal
    qd3b = eval(stringify_operation(operator, 'qd1.value', 'qd2'))
    if operator != DIVMOD:
        assert isinstance(qd3b, QuantizedDecimal)
    assert qd3b == qd3

    if '(' not in operator:
        # Test in-place operator
        exec(stringify_operation(operator + '=', 'qd1', 'qd2'))
        assert qd1 == qd3


@pytest.mark.unit
@pytest.mark.parametrize('operator', [ABS, '+', '-'])
@pytest.mark.parametrize('number', ['2.718281828'])
@pytest.mark.parametrize('precision', [9])
def test_quantized_decimal_unary_math(operator, number, precision):
    """Test quantized decimal unary operations"""
    qd1 = QuantizedDecimal(number, precision)
    assert qd1 == qd1.value

    qd2 = eval(stringify_operation(operator, 'qd1'))
    qd2_value = eval(stringify_operation(operator, 'qd1.value'))
    assert isinstance(qd2, QuantizedDecimal)

    quant = 1 / (Decimal(10) ** Decimal(precision))
    qd2_value = qd2_value.quantize(quant)
    assert qd2 == qd2_value


@pytest.mark.unit
@pytest.mark.parametrize('operator', [COMPLEX, FLOAT, INT])
@pytest.mark.parametrize('number', [2 ** 63 + 0.1234567])
@pytest.mark.parametrize('precision', [7])
def test_quantized_decimal_type_cast(operator, number, precision):
    """Test quantized decimal type casts"""
    qd1 = QuantizedDecimal(number, precision)
    assert qd1 == qd1.value

    qd2 = eval(stringify_operation(operator, 'qd1'))
    qd2_value = eval(stringify_operation(operator, 'qd1.value'))

    assert qd2 == qd2_value
    assert type(qd2) is type(qd2_value)
