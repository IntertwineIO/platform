#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
@pytest.mark.smoke
def test_decode_problem(options):
    '''Tests decoding a standard problem'''


@pytest.mark.unit
@pytest.mark.smoke
def test_decode_problem_connection(options):
    '''Tests decoding a standard problem connection'''


@pytest.mark.unit
@pytest.mark.smoke
def test_decode_problem_connection_rating(options):
    '''Tests decoding a standard problem connection rating'''


@pytest.mark.unit
@pytest.mark.smoke
def test_incremental_decode(options):
    '''Tests decoding incrementally'''
