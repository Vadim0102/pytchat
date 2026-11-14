from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _extract_shortcut(emoji: Dict[str, Any]) -> str:
    shortcuts = emoji.get("shortcuts") or []
    if shortcuts:
        return shortcuts[0]
    emoji_id = emoji.get("emojiId")
    if emoji_id:
        return emoji_id
    return ""


def _extract_emoji_payload(emoji: Dict[str, Any]) -> Dict[str, Any]:
    image = emoji.get("image") or {}
    thumbs = image.get("thumbnails") or []
    url = thumbs[0].get("url") if thumbs else ""
    shortcut = _extract_shortcut(emoji)
    return {
        "emojiId": emoji.get("emojiId"),
        "shortcuts": emoji.get("shortcuts") or [],
        "text": shortcut,
        "url": url,
    }


def _find_emoji_fountain_entity(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        entity = value.get("emojiFountainDataEntity")
        if isinstance(entity, dict):
            return entity
        for child in value.values():
            found = _find_emoji_fountain_entity(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_emoji_fountain_entity(child)
            if found is not None:
                return found
    return None


def parse_raw_chat_action(action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(action, dict):
        return None

    entity = _find_emoji_fountain_entity(action)
    if entity is None and "reactionBuckets" in action and "updateTimeUsec" in action:
        entity = action
    if entity is not None:
        buckets = []
        for bucket in entity.get("reactionBuckets") or []:
            if not isinstance(bucket, dict):
                continue
            duration = bucket.get("duration") or {}
            buckets.append({
                "totalReactions": bucket.get("totalReactions", 0),
                "durationSeconds": duration.get("seconds"),
                "intensityScore": bucket.get("intensityScore"),
                "reactionsData": [
                    {
                        "unicodeEmojiId": reaction.get("unicodeEmojiId"),
                        "reactionCount": reaction.get("reactionCount", 0),
                    }
                    for reaction in bucket.get("reactionsData") or []
                    if isinstance(reaction, dict)
                ],
            })
        return {
            "type": "emoji_fountain_update",
            "key": entity.get("key"),
            "reactionBuckets": buckets,
            "updateTimeUsec": entity.get("updateTimeUsec"),
            "raw": entity,
        }

    add_chat = action.get("addChatItemAction") or {}
    item = add_chat.get("item")
    if not isinstance(item, dict):
        return None

    renderer = None
    for key in (
        "liveChatTextMessageRenderer",
        "liveChatPaidMessageRenderer",
        "liveChatPaidStickerRenderer",
        "liveChatMembershipItemRenderer",
        "liveChatDonationAnnouncementRenderer",
        "liveChatViewerEngagementMessageRenderer",
        "liveChatModeChangeMessageRenderer",
        "liveChatSponsorshipsGiftPurchaseAnnouncementRenderer",
        "liveChatSponsorshipsGiftRedemptionAnnouncementRenderer",
    ):
        if key in item:
            renderer = item[key]
            break

    if renderer is None:
        return None

    author_name = ""
    author_name_block = renderer.get("authorName") or {}
    if isinstance(author_name_block, dict):
        author_name = author_name_block.get("simpleText") or ""

    message_runs = (renderer.get("message") or {}).get("runs") or []
    message_parts: List[str] = []
    message_ex: List[Any] = []
    emojis: List[Dict[str, Any]] = []

    for run in message_runs:
        if not isinstance(run, dict):
            continue

        if "emoji" in run:
            emoji = run["emoji"]
            shortcut = _extract_shortcut(emoji)
            if shortcut:
                message_parts.append(shortcut)
            payload = _extract_emoji_payload(emoji)
            if payload.get("emojiId") or payload.get("text"):
                emojis.append(payload)
            message_ex.append(payload)
            continue

        text = run.get("text")
        if text:
            message_parts.append(text)
            message_ex.append(text)

    if not message_parts and "text" in (renderer.get("message") or {}):
        message_parts.append(_coerce_text((renderer.get("message") or {}).get("text")))

    message = "".join(message_parts)
    author_photo = ""
    author_photo_block = renderer.get("authorPhoto") or {}
    thumbs = author_photo_block.get("thumbnails") or []
    if thumbs:
        author_photo = thumbs[-1].get("url") or ""

    timestamp_usec = renderer.get("timestampUsec")
    if timestamp_usec is None:
        timestamp_usec = action.get("timestampUsec")
    if timestamp_usec is not None:
        try:
            timestamp_usec = int(timestamp_usec)
        except (TypeError, ValueError):
            timestamp_usec = None

    dt_value = None
    if timestamp_usec is not None:
        dt_value = datetime.fromtimestamp(timestamp_usec / 1000000).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "type": "textMessage",
        "id": renderer.get("id"),
        "message": message,
        "messageEx": message_ex,
        "emojis": emojis,
        "timestampUsec": timestamp_usec,
        "datetime": dt_value,
        "author": {
            "name": author_name,
            "channelId": renderer.get("authorExternalChannelId"),
            "photoUrl": author_photo,
        },
    }
