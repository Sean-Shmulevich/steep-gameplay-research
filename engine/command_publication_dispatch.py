"""Recovered local decoder following the observed generic publication store.

See REQUEST_COMMAND_LIFECYCLE.md, Publication-store dispatch decoder.
This models selected integer effects only, not every register/flag or a whole VM.
The caller reads encoded_word at old instruction-stream pointer minus four.
No native reads, writes, execution or lifetime management occur here.
"""


def decode_store_dispatch(encoded_word, rolling_key):
    """Return signed handler displacement and updated 64-bit rolling key."""
    if type(encoded_word) is not int or not 0 <= encoded_word < 2**32:
        raise ValueError('encoded word must be uint32')
    if type(rolling_key) is not int or not 0 <= rolling_key < 2**64:
        raise ValueError('rolling key must be uint64')
    mask = 0xffffffff

    def swap(value):
        return int.from_bytes(value.to_bytes(4, 'little'), 'big')

    value = ((encoded_word ^ (rolling_key & mask)) + 1) & mask
    value = swap(value ^ 0x73640df2)
    value = ((value + 1) & mask) ^ 0x50486a2a
    value = swap((value - 1) & mask)
    value = (-((value - 0x017f06f9) & mask)) & mask
    return dict(stream_bytes_consumed=4, decoded_word=value,
                handler_delta=value if value < 0x80000000 else value - 2**32,
                rolling_key=rolling_key ^ value)
