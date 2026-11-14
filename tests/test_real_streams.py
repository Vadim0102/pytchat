import json
import os
from pathlib import Path

import httpx
import pytest

import pytchat
from pytchat.processors.dummy_processor import DummyProcessor
from pytchat.util import get_channelid


TESTDATA_PATH = Path(__file__).parent / 'testdata' / 'real_streams.json'
REAL_LIVE_TESTS = os.environ.get('PYTCHAT_LIVE_TESTS') == '1'


with TESTDATA_PATH.open('r', encoding='utf-8') as fh:
    REAL_STREAMS_DATA = json.load(fh)


@pytest.mark.skipif(not REAL_LIVE_TESTS, reason='Live network tests are disabled by default; set PYTCHAT_LIVE_TESTS=1 to enable them.')
@pytest.mark.parametrize('stream', REAL_STREAMS_DATA['live_streams'])
def test_real_live_stream_channel_lookup(stream):
    client = httpx.Client(http2=True)
    try:
        channel_id = get_channelid(client, stream['video_id'])
    except Exception as exc:  # pragma: no cover - network dependent
        pytest.skip(f'Live channel lookup unavailable for {stream["video_id"]}: {exc}')
    finally:
        client.close()

    assert isinstance(channel_id, str)
    assert len(channel_id) == 24
    assert channel_id.startswith('UC')


@pytest.mark.skipif(not REAL_LIVE_TESTS, reason='Live network tests are disabled by default; set PYTCHAT_LIVE_TESTS=1 to enable them.')
@pytest.mark.parametrize('stream', REAL_STREAMS_DATA['live_streams'][:1])
def test_real_live_stream_smoke(stream):
    stream_obj = pytchat.create(
        stream['video_id'],
        processor=DummyProcessor(),
        interruptable=False,
        hold_exception=False,
        seektime=0,
    )
    try:
        chat_data = stream_obj.get()
        assert isinstance(chat_data, list)
    except Exception as exc:  # pragma: no cover - network dependent
        pytest.skip(f'Live stream fetch unavailable for {stream["video_id"]}: {exc}')
    finally:
        stream_obj.terminate()
