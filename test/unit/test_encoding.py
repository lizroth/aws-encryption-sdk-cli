# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""Unit test suite for ``aws_encryption_sdk_cli.internal.encoding``."""
import base64
import io
import os

import pytest

from aws_encryption_sdk_cli.internal.encoding import Base64IO


def test_base64io_bad_wrap():
    with pytest.raises(TypeError) as excinfo:
        Base64IO(7)

    excinfo.match(r'Base64IO wrapped object must have attributes: *')


def test_base64io_write_outside_context_manager():
    test = Base64IO(io.BytesIO())

    with pytest.raises(ValueError) as excinfo:
        test.write(b'asuhdfiouhsad')

    excinfo.match(r'Writes are only allowed on Base64IO objects when used as context managers.')


def test_base64io_write_after_closed():
    with Base64IO(io.BytesIO()) as test:
        with pytest.raises(ValueError) as excinfo:
            test.close()
            test.write(b'aksdhjf')

    excinfo.match(r'I/O operation on closed file.')


def test_base64io_read_after_closed():
    with Base64IO(io.BytesIO()) as test:
        with pytest.raises(ValueError) as excinfo:
            test.close()
            test.read()

    excinfo.match(r'I/O operation on closed file.')


def test_base64io_seekable():
    test = Base64IO(io.BytesIO())

    assert not test.seekable


def test_base64io_seek():
    test = Base64IO(io.BytesIO())

    with pytest.raises(IOError) as excinfo:
        test.seek(4)

    excinfo.match(r'Seek not allowed on Base64IO objects')


TEST_CASES = (
    (1024, 1024),
    (222, 222),
    (1024, None),
    (1024, 5),
    (5, 1024)
)


@pytest.mark.parametrize('source_bytes, read_bytes', TEST_CASES)
def test_base64io_decode(source_bytes, read_bytes):
    plaintext_source = os.urandom(source_bytes)
    plaintext_b64 = io.BytesIO(base64.b64encode(plaintext_source))
    plaintext_wrapped = Base64IO(plaintext_b64)

    test = plaintext_wrapped.read(read_bytes)

    if source_bytes == read_bytes or read_bytes is None:
        assert test == plaintext_source
    else:
        assert test == plaintext_source[:read_bytes]


@pytest.mark.parametrize('source_bytes', [case[0] for case in TEST_CASES])
def test_base64io_encode(source_bytes):
    plaintext_source = os.urandom(source_bytes)
    plaintext_b64 = base64.b64encode(plaintext_source)
    plaintext_stream = io.BytesIO()

    with Base64IO(plaintext_stream) as plaintext_wrapped:
        plaintext_wrapped.write(plaintext_source)

    assert plaintext_stream.getvalue() == plaintext_b64


def test_base64io_decode_context_manager():
    source_plaintext = os.urandom(102400)
    source_stream = io.BytesIO(base64.b64encode(source_plaintext))

    test = io.BytesIO()
    with Base64IO(source_stream) as stream:
        for chunk in stream:
            test.write(chunk)

    assert test.getvalue() == source_plaintext


def test_base64io_decode_readlines():
    source_plaintext = os.urandom(102400)
    source_stream = io.BytesIO(base64.b64encode(source_plaintext))

    test = io.BytesIO()
    with Base64IO(source_stream) as stream:
        for chunk in stream.readlines():
            test.write(chunk)

    assert test.getvalue() == source_plaintext


def test_base64io_decode_file(tmpdir):
    source_plaintext = os.urandom(1024 * 1024)
    b64_plaintext = tmpdir.join('base64_plaintext')
    b64_plaintext.write(base64.b64encode(source_plaintext))
    decoded_plaintext = tmpdir.join('decoded_plaintext')

    with open(str(b64_plaintext), 'rb') as source, open(str(decoded_plaintext), 'wb') as raw:
        with Base64IO(source) as decoder:
            for chunk in decoder:
                raw.write(chunk)

    with open(str(decoded_plaintext), 'rb') as raw:
        decoded = raw.read()

    assert decoded == source_plaintext


def test_base64io_encode_file(tmpdir):
    source_plaintext = os.urandom(1024 * 1024)
    plaintext_b64 = base64.b64encode(source_plaintext)
    plaintext = tmpdir.join('plaintext')
    b64_plaintext = tmpdir.join('base64_plaintext')

    with open(str(plaintext), 'wb') as file:
        file.write(source_plaintext)

    with open(str(plaintext), 'rb') as source, open(str(b64_plaintext), 'wb') as target:
        with Base64IO(target) as encoder:
            for chunk in source:
                encoder.write(chunk)

    with open(str(b64_plaintext), 'rb') as file2:
        encoded = file2.read()

    assert encoded == plaintext_b64
