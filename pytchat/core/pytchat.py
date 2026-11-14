import httpx
import json
import logging
import os
import signal
import time
import traceback
from ..parser.live import Parser
from .. import config
from .. import exceptions
from ..paramgen import liveparam, arcparam
from ..processors.default.processor import DefaultProcessor
from ..processors.combinator import Combinator
from .. import util

headers = config.headers
MAX_RETRY = 10

class PytchatCore:
    '''

    Parameter
    ---------
    video_id : str

    seektime : int
        start position of fetching chat (seconds).
        This option is valid for archived chat only.
        If negative value, chat data posted before the start of the broadcast
        will be retrieved as well.

    processor : ChatProcessor

    client : httpx.Client
        The client for connecting youtube.
        You can specify any customized httpx client (e.g. coolies, user agent).

    interruptable : bool
        Allows keyboard interrupts.
        Set this parameter to False if your own multi-threading program causes
        the problem.

    force_replay : bool
        force to fetch archived chat data, even if specified video is live.

    topchat_only : bool
        If True, get only top chat.

    hold_exception : bool [default:True]
        If True, when exceptions occur, the exception is held internally,
        and can be raised by raise_for_status().

    replay_continuation : str
        If this parameter is not None, the processor will attempt to get chat data from continuation.
        This parameter is only allowed in archived mode.

    Attributes
    ---------
    _is_alive : bool
        Flag to stop getting chat.
    '''

    def __init__(self, video_id,
                 seektime=-1,
                 processor=DefaultProcessor(),
                 client=None,
                 interruptable=True,
                 force_replay=False,
                 topchat_only=False,
                 hold_exception=True,
                 logger=None,
                 replay_continuation=None,
                 verbose=False
                 ):
        if logger is None:
            env_verbose = str(os.environ.get('PYTCHAT_VERBOSE_LOGS', '')).lower() in {'1', 'true', 'yes', 'on'}
            logger = config.logger(__name__, logging.DEBUG if (verbose or env_verbose) else logging.INFO)
        if client is None:
            client = httpx.Client(http2=True)
        self._client = client
        self._video_id = util.extract_video_id(video_id)
        self.seektime = seektime
        if isinstance(processor, tuple):
            self.processor = Combinator(processor)
        else:
            self.processor = processor
        self._is_alive = True
        self._is_replay = force_replay or (replay_continuation is not None)
        self._hold_exception = hold_exception
        self._exception_holder = None
        self._parser = Parser(
            is_replay=self._is_replay,
            exception_holder=self._exception_holder
        )
        self._first_fetch = replay_continuation is None
        self._fetch_url = config._sml if replay_continuation is None else config._smr
        self._topchat_only = topchat_only
        self._dat = ''
        self._last_offset_ms = 0
        self._logger = logger
        self._logger.debug(f"Initialized PytchatCore for video_id={self._video_id}, seektime={seektime}, replay={self._is_replay}, verbose={verbose or str(os.environ.get('PYTCHAT_VERBOSE_LOGS', '')).lower() in {'1','true','yes','on'}}")
        self.continuation = replay_continuation
        if interruptable:
            signal.signal(signal.SIGINT, lambda a, b: self.terminate())
        self._setup()

    def _setup(self):
        if not self.continuation:
            time.sleep(0.1)  # sleep shortly to prohibit skipping fetching data
            """Fetch first continuation parameter,
            create and start _listen loop.
            """
            self._logger.debug(f"Fetching initial continuation for video_id={self._video_id}")
            channel_id = util.get_channelid(self._client, self._video_id)
            self._logger.debug(f"Resolved channel_id={channel_id} for video_id={self._video_id}")
            self.continuation = liveparam.getparam(
                self._video_id,
                channel_id=channel_id,
                past_sec=3)
            self._logger.debug(f"Initial continuation acquired for video_id={self._video_id}: {self.continuation[:30]}...")

    def _get_chat_component(self):
        ''' Fetch chat data and store them into buffer,
        get next continuaiton parameter and loop.

        Parameter
        ---------
        continuation : str
            parameter for next chat data
        '''
        try:
            if self.continuation and self._is_alive:
                self._logger.debug(f"Requesting next chat batch for video_id={self._video_id}, continuation={self.continuation[:30]}...")
                contents = self._get_contents(self.continuation, self._client, headers)
                metadata, chatdata = self._parser.parse(contents)
                chatdata = chatdata or []
                timeout = metadata['timeoutMs'] / 1000
                chat_component = {
                    "video_id": self._video_id,
                    "timeout": timeout,
                    "chatdata": chatdata,
                    "updates": metadata.get('updates', [])
                }
                self.continuation = metadata.get('continuation')
                self._last_offset_ms = metadata.get('last_offset_ms', 0)
                self._logger.debug(
                    f"Received chat batch for video_id={self._video_id}: items={len(chatdata) if chatdata else 0}, "
                    f"updates={len(metadata.get('updates', []))}, "
                    f"timeout={timeout}s, next_continuation={bool(self.continuation)}"
                )
                return chat_component
        except exceptions.ChatParseException as e:
            self._logger.debug(f"[{self._video_id}]{str(e)}")
            self._raise_exception(e)
        except Exception as e:
            self._logger.error(f"{traceback.format_exc(limit=-1)}")
            self._raise_exception(e)

    def _get_contents(self, continuation, client, headers):
        '''Get 'continuationContents' from livechat json.
           If contents is None at first fetching,
           try to fetch archive chat data.

          Return:
          -------
            'continuationContents' which includes metadata & chat data.
        '''
        self._logger.debug(f"Fetching livechat payload for video_id={self._video_id}, replay={self._is_replay}, offset_ms={self._last_offset_ms}")
        livechat_json = self._get_livechat_json(
            continuation, client, replay=self._is_replay, offset_ms=self._last_offset_ms)
        contents, dat = self._parser.get_contents(livechat_json)
        if self._dat == '' and dat:
            self._dat = dat
        if self._first_fetch:
            if contents is None or self._is_replay:
                '''Try to fetch archive chat data.'''
                self._logger.debug(f"Falling back to archived chat for video_id={self._video_id}")
                self._parser.is_replay = True
                self._fetch_url = config._smr
                channel_id = util.get_channelid(client, self._video_id)
                continuation = arcparam.getparam(
                    self._video_id, self.seektime, self._topchat_only, channel_id)
                livechat_json = self._get_livechat_json(
                    continuation, client, replay=True, offset_ms=self.seektime * 1000)
                reload_continuation = self._parser.reload_continuation(
                    self._parser.get_contents(livechat_json)[0])
                if reload_continuation:
                    self._logger.debug(f"Reloading continuation for replay fetch: {reload_continuation[:30]}...")
                    livechat_json = (self._get_livechat_json(
                        reload_continuation, client, headers))
                contents, _ = self._parser.get_contents(livechat_json)
                self._is_replay = True
            self._first_fetch = False
        return contents

    def _get_livechat_json(self, continuation, client, replay: bool, offset_ms: int = 0):
        '''
        Get json which includes chat data.
        '''
        livechat_json = None
        err = None
        if offset_ms < 0:
            offset_ms = 0
        param = util.get_param(continuation, dat=self._dat, replay=replay, offsetms=offset_ms)
        self._logger.debug(f"POST livechat fetch for video_id={self._video_id}, replay={replay}, offset_ms={offset_ms}")
        for attempt in range(1, MAX_RETRY + 2):
            try:
                response = client.post(self._fetch_url, json=param)
                livechat_json = response.json()
                self._logger.debug(f"Livechat fetch succeeded for video_id={self._video_id} on attempt {attempt}")
                break
            except (json.JSONDecodeError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
                err = e
                self._logger.debug(f"Livechat fetch failed for video_id={self._video_id} on attempt {attempt}/{MAX_RETRY + 1}: {e}")
                time.sleep(2)
                continue
        else:
            self._logger.error(f"[{self._video_id}]"
                               f"Exceeded retry count. Last error: {str(err)}")
            self._raise_exception(exceptions.RetryExceedMaxCount())
        return livechat_json

    def get(self):
        if not self.is_alive():
            return []

        chat_component = self._get_chat_component()
        if chat_component is None:
            return []

        return self.processor.process([chat_component])

    def is_replay(self):
        return self._is_replay

    def is_alive(self):
        return self._is_alive

    def terminate(self):
        if not self.is_alive():
            return
        self._is_alive = False
        self.processor.finalize()

    def raise_for_status(self):
        if self._exception_holder is not None:
            raise self._exception_holder

    def _raise_exception(self, exception: Exception = None):
        self.terminate()
        if self._hold_exception is False:
            raise exception
        self._exception_holder = exception
