from unittest.mock import Mock

from pytchat.core.pytchat import PytchatCore
from pytchat.parser.live import Parser
from pytchat.processors.raw_parser import parse_raw_chat_action


RAW_ACTION = {
    'addChatItemAction': {
        'item': {
            'liveChatTextMessageRenderer': {
                'message': {
                    'runs': [
                        {'text': 'Why DID YOUTUBE HAVE TO BAN OMG'},
                        {'emoji': {'emojiId': '😢', 'shortcuts': [':crying_face:'], 'image': {'thumbnails': [{'url': 'https://example.test/emoji.png'}]}}},
                        {'emoji': {'emojiId': '😢', 'shortcuts': [':crying_face:'], 'image': {'thumbnails': [{'url': 'https://example.test/emoji.png'}]}}},
                        {'emoji': {'emojiId': '😢', 'shortcuts': [':crying_face:'], 'image': {'thumbnails': [{'url': 'https://example.test/emoji.png'}]}}},
                        {'text': ' THE SSSSTTRRREEAAMMM'},
                    ]
                },
                'authorName': {'simpleText': '@CyreneLavender'},
                'authorExternalChannelId': 'UC123',
                'authorPhoto': {'thumbnails': [{'url': 'https://example.test/avatar.png'}]},
                'id': 'msg-1',
                'timestampUsec': '1582402421197748',
            }
        }
    }
}


def test_parse_raw_chat_action_with_reactions():
    parsed = parse_raw_chat_action(RAW_ACTION)

    assert parsed is not None
    assert parsed['id'] == 'msg-1'
    assert parsed['author']['name'] == '@CyreneLavender'
    assert parsed['message'] == 'Why DID YOUTUBE HAVE TO BAN OMG:crying_face::crying_face::crying_face: THE SSSSTTRRREEAAMMM'
    assert len(parsed['emojis']) == 3
    assert parsed['emojis'][0]['emojiId'] == '😢'
    assert parsed['emojis'][0]['text'] == ':crying_face:'
    assert parsed['timestampUsec'] == 1582402421197748
    assert parsed['datetime']


def test_parse_emoji_fountain_update():
    update = {
        'payload': {
            'emojiFountainDataEntity': {
                'key': 'opaque-key',
                'reactionBuckets': [
                    {
                        'totalReactions': 7,
                        'duration': {'seconds': '1'},
                        'intensityScore': 2,
                        'reactionsData': [
                            {'unicodeEmojiId': '🎉', 'reactionCount': 7},
                        ],
                    }
                ],
                'updateTimeUsec': '1794654639868520',
            }
        }
    }

    parsed = parse_raw_chat_action(update)

    assert parsed['type'] == 'emoji_fountain_update'
    assert parsed['key'] == 'opaque-key'
    assert parsed['reactionBuckets'] == [{
        'totalReactions': 7,
        'durationSeconds': '1',
        'intensityScore': 2,
        'reactionsData': [
            {'unicodeEmojiId': '🎉', 'reactionCount': 7},
        ],
    }]
    assert parsed['updateTimeUsec'] == '1794654639868520'


def test_parser_preserves_emoji_fountain_updates_from_response():
    response = {
        'continuationContents': {
            'liveChatContinuation': {
                'continuations': [{'timedContinuationData': {
                    'timeoutMs': 1000,
                    'continuation': 'next',
                }}],
                'actions': [],
            }
        },
        'payload': {
            'emojiFountainDataEntity': {
                'key': 'opaque-key',
                'reactionBuckets': [],
                'updateTimeUsec': '1794654639868520',
            }
        },
    }

    parser = Parser(is_replay=False)
    contents, _ = parser.get_contents(response)
    metadata, chatdata = parser.parse(contents)

    assert chatdata == []
    assert metadata['updates'][0]['key'] == 'opaque-key'
    assert parse_raw_chat_action(metadata['updates'][0])['type'] == 'emoji_fountain_update'


def test_empty_chat_batch_is_iterable():
    chat = object.__new__(PytchatCore)
    chat.continuation = 'continuation'
    chat._is_alive = True
    chat._video_id = 'video-id'
    chat._client = Mock()
    chat.processor = Mock()
    chat._logger = Mock()
    chat._parser = Mock()
    chat._parser.parse.return_value = (
        {'timeoutMs': 1000, 'continuation': 'next-continuation'},
        None,
    )
    chat._get_contents = Mock()

    component = chat._get_chat_component()

    assert component['chatdata'] == []
