"""
pytchat.parser.live
~~~~~~~~~~~~~~~~~~~
Parser of live chat JSON.
"""

from .. import exceptions


class Parser:
    '''
    Parser of chat json.
    
    Parameter
    ----------
    is_replay : bool

    exception_holder : Object [default:Npne]
        The object holding exceptions.
        This is passed from the parent livechat object.
    '''
    __slots__ = ['is_replay', 'exception_holder']

    def __init__(self, is_replay, exception_holder=None):
        self.is_replay = is_replay
        self.exception_holder = exception_holder

    def get_contents(self, jsn):
        if jsn is None:
            self.raise_exception(exceptions.IllegalFunctionCall('Called with none JSON object.'))
        if jsn.get("responseContext", {}).get("errors"):
            raise exceptions.ResponseContextError(
                'The video_id would be wrong, or video is deleted or private.')
        contents = jsn.get('continuationContents')
        updates = self._find_emoji_fountain_updates(jsn)
        if contents is not None and updates:
            contents = dict(contents)
            live_chat = contents.get('liveChatContinuation')
            if live_chat is not None:
                live_chat = dict(live_chat)
                live_chat['_pytchat_updates'] = updates
                contents['liveChatContinuation'] = live_chat
        visitor_data = jsn.get("responseContext", {}).get("visitorData")
        return contents, visitor_data

    def _find_emoji_fountain_updates(self, value):
        updates = []

        def visit(node):
            if isinstance(node, dict):
                entity = node.get('emojiFountainDataEntity')
                if isinstance(entity, dict):
                    updates.append(entity)
                for child in node.values():
                    visit(child)
            elif isinstance(node, list):
                for child in node:
                    visit(child)

        visit(value)
        return updates

    def parse(self, contents):
        """
        Parameter
        ----------
        + contents : dict
            + JSON of chat data from YouTube.

        Returns
        -------
        tuple:
        + metadata : dict
         + timeout
         + video_id
         + continuation
        + chatdata : List[dict]
        """

        if contents is None:
            '''Broadcasting end or cannot fetch chat stream'''
            self.raise_exception(exceptions.NoContents('Chat data stream is empty.'))

        cont = contents['liveChatContinuation']['continuations'][0]
        if cont is None:
            self.raise_exception(exceptions.NoContinuation('No Continuation'))
        metadata = (cont.get('invalidationContinuationData')
                    or cont.get('timedContinuationData')
                    or cont.get('reloadContinuationData')
                    or cont.get('liveChatReplayContinuationData')
                    )
        if metadata is None:
            if cont.get("playerSeekContinuationData"):
                self.raise_exception(exceptions.ChatDataFinished('Finished chat data'))
            unknown = list(cont.keys())[0]
            if unknown:
                self.raise_exception(exceptions.ReceivedUnknownContinuation(
                    f"Received unknown continuation type:{unknown}"))
            else:
                self.raise_exception(exceptions.FailedExtractContinuation('Cannot extract continuation data'))
        return self._create_data(metadata, contents)

    def reload_continuation(self, contents):
        """
        When `seektime == 0` or seektime is abbreviated ,
        check if fetched chat json has no chat data.
        If so, try to fetch playerSeekContinuationData.
        This function must be run only first fetching.
        """
        if contents is None:
            '''Broadcasting end or cannot fetch chat stream'''
            self.raise_exception(exceptions.NoContents('Chat data stream is empty.'))
        cont = contents['liveChatContinuation']['continuations'][0]

        if cont.get("liveChatReplayContinuationData"):
            # chat data exist.
            return None
        # chat data do not exist, get playerSeekContinuationData.
        init_cont = cont.get("playerSeekContinuationData")
        if init_cont:
            return init_cont.get("continuation")
        self.raise_exception(exceptions.ChatDataFinished('Finished chat data'))

    def _create_data(self, metadata, contents):
        live_chat = contents['liveChatContinuation']
        actions = live_chat.get('actions') or []
        updates = live_chat.get('_pytchat_updates') or []
        if self.is_replay:
            last_offset_ms = self._get_lastoffset(actions)
            metadata.setdefault("timeoutMs", 5000)
            metadata.setdefault("last_offset_ms", last_offset_ms)
            """Archived chat has different structures than live chat,
            so make it the same format."""
            chatdata = [action["replayChatItemAction"]["actions"][0]
                        for action in actions]
        else:
            metadata.setdefault('timeoutMs', 5000)
            chatdata = actions
        if updates:
            metadata = dict(metadata)
            metadata['updates'] = updates
        return metadata, chatdata

    def _get_lastoffset(self, actions: list):
        if actions:
            return int(actions[-1]["replayChatItemAction"]["videoOffsetTimeMsec"])
        return 0

    def raise_exception(self, exception):
        if self.exception_holder is None:
            raise exception
        self.exception_holder = exception
