# -*- coding: utf-8 -*-
import asyncio
import inspect

import wrapt
from pprint import PrettyPrinter

DELIMITER = '–'  # chr(8211)
WIDTH = 200
SEPARATOR = DELIMITER * WIDTH
DEBUG_WRAPPERS = {'async_debug_wrapper', 'sync_debug_wrapper'}


def offset_text(text, offset_space):
    """Offset text by given space with proper newline handling"""
    lines = text.split('\n')
    offset_lines = (offset_space + line for line in lines)
    offset_text = '\n'.join(offset_lines)
    return offset_text


def format_text(label, text, offset_space):
    """Format text with given label and space with newline handling"""
    if '\n' in text:
        print(f'{offset_space}{label}:')
        print(f'{offset_text(text, offset_space)}')
    else:
        print(f'{offset_space}{label}: {text}')


def derive_offset_space(offset=None, indent=4):
    """Derive offset by counting wrapped stack frames if not given"""
    if offset is None:
        frame_records = inspect.stack()
        new_offset = sum(1 for f in frame_records
                         if f.function in DEBUG_WRAPPERS) - 1
    else:
        new_offset = offset
    return ' ' * new_offset * indent


def evaluate_context(self, context):
    try:
        evaluated_context = eval(context)
    except Exception:
        evaluated_context = None
    return str(evaluated_context)


def loop_repr(loop):
    class_name, running, closed, debug = repr(loop)[1:-1].split()
    module = loop.__class__.__module__
    hex_id = hex(id(loop))
    return f'<{module}.{class_name} object at {hex_id} {running} {closed} {debug}>'


def print_enter_info(wrapped, context, instance, args, kwargs,
                     printer, offset_space, loop=None, is_async=False):
    """Print enter info for wrapped function to be called/awaited"""
    print(SEPARATOR)
    async_ = 'async ' if is_async else ''
    print(f'{offset_space}Entering {async_}{wrapped.__name__}')
    if instance is not None:
        if context is not None:
            format_text('context', evaluate_context(instance, context), offset_space)
        format_text('instance', repr(instance), offset_space)
    format_text('args', printer.pformat(args), offset_space)
    format_text('kwargs', printer.pformat(kwargs), offset_space)
    loop = loop or asyncio.get_event_loop()
    format_text('loop', loop_repr(loop), offset_space)
    start_time = loop.time()
    format_text('start', str(start_time), offset_space)
    print(SEPARATOR)


def print_exit_info(wrapped, context, instance, args, kwargs,
                    result, end_time, elapsed_time,
                    printer, offset_space, loop=None, is_async=False):
    """Print exit info for wrapped function to be called/awaited"""
    print(SEPARATOR)
    async_ = 'async ' if is_async else ''
    print(f'{offset_space}Returning from {async_}{wrapped.__name__}')
    if instance is not None:
        if context is not None:
            format_text('context', evaluate_context(instance, context), offset_space)
        format_text('instance', repr(instance), offset_space)
    format_text('args', printer.pformat(args), offset_space)
    format_text('kwargs', printer.pformat(kwargs), offset_space)
    format_text('return', printer.pformat(result), offset_space)
    loop = loop or asyncio.get_event_loop()
    format_text('loop', loop_repr(loop), offset_space)
    format_text('end', str(end_time), offset_space)
    format_text('elapsed', str(elapsed_time), offset_space)
    print(SEPARATOR)


def sync_debug(offset=None, indent=4, context=None):
    """
    Sync Debug

    Decorator for synchronous functions to provide debugging info:
    - Upon entering: args/kwargs, instance repr (if method) & start time
    - Upon exiting: args/kwargs, instance repr (if method), return value
      & end/elapsed time (args/kwargs/instance are repeated since the
      return message can be far removed from the await message)
    - Each message is offset based on the degree to which the function
      is awaited by other functions also decorated by Debug/Async Debug
    - Horizontal separators visually delineate each message

    I/O:
    offset=None:    By default, offset increases automatically with each
                    level of decorated debug call, but this parameter
                    allows it to be overridden
    indent=4:       Integer specifying the number of spaces to be used
                    for each level of offset
    """
    @wrapt.decorator
    def sync_debug_wrapper(wrapped, instance, args, kwargs):
        loop = asyncio.get_event_loop()
        offset_space = derive_offset_space(offset, indent)
        width = WIDTH - len(offset_space)
        printer = PrettyPrinter(indent=indent, width=width)
        print_enter_info(wrapped, context, instance, args, kwargs,
                         printer, offset_space, loop)

        true_start_time = loop.time()
        result = wrapped(*args, **kwargs)
        end_time = loop.time()
        elapsed_time = end_time - true_start_time

        print_exit_info(wrapped, context, instance, args, kwargs,
                        result, end_time, elapsed_time,
                        printer, offset_space, loop)
        return result

    return sync_debug_wrapper


def async_debug(offset=None, indent=4, context=None):
    """
    Async Debug

    Decorator for async functions/methods to provide debugging info:
    - Upon entering: args/kwargs, instance repr (if method) & start time
    - Upon exiting: args/kwargs, instance repr (if method), return value
      & end/elapsed time (args/kwargs/instance are repeated since the
      return message can be far removed from the await message)
    - Each message is offset based on the degree to which the function
      is awaited by other functions also decorated by Debug/Async Debug
    - Horizontal separators visually delineate each message

    I/O:
    offset=None:    By default, offset increases automatically with each
                    level of decorated debug call, but this parameter
                    allows it to be overridden
    indent=4:       Integer specifying the number of spaces to be used
                    for each level of offset
    """
    @wrapt.decorator
    async def async_debug_wrapper(wrapped, instance, args, kwargs):
        loop = asyncio.get_event_loop()
        offset_space = derive_offset_space(offset, indent)
        width = WIDTH - len(offset_space)
        printer = PrettyPrinter(indent=indent, width=width)
        print_enter_info(wrapped, context, instance, args, kwargs,
                         printer, offset_space, loop, is_async=True)

        true_start_time = loop.time()
        result = await wrapped(*args, **kwargs)
        end_time = loop.time()
        elapsed_time = end_time - true_start_time

        print_exit_info(wrapped, context, instance, args, kwargs,
                        result, end_time, elapsed_time,
                        printer, offset_space, loop, is_async=True)
        return result

    return async_debug_wrapper
