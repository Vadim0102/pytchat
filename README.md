# FORK pytchat

A maintained fork of **pytchat**, a Python library for fetching YouTube Live Chat messages.

<br><br><br>

## Description

This repository is a maintained fork of the original **pytchat** project.

`pytchat` is a Python library for fetching YouTube Live Chat messages **without using Selenium or BeautifulSoup**.

### Features

- Customizable [chat data processors](https://github.com/taizan-hokuto/pytchat/wiki/ChatProcessor), including a YouTube API-compatible processor.
- Asyncio support.
- Fast retrieval of initial chat data by generating continuation parameters instead of relying on web scraping.
- Updated to keep the library working with recent YouTube changes.

For more detailed information, see the [wiki](https://github.com/taizan-hokuto/pytchat/wiki). <br>
[wiki (Japanese)](https://github.com/taizan-hokuto/pytchat/wiki/Home_jp)

## Installation (Fork)

```bash
pip install git+https://github.com/Vadim0102/pytchat.git
```

## Examples

### Fetch chat data (see [wiki](https://github.com/taizan-hokuto/pytchat/wiki/PytchatCore))

```python
import pytchat

chat = pytchat.create(video_id="uIx8l2xlYVY")

while chat.is_alive():
    for c in chat.get().items:
        print(f"{c.datetime} [{c.author.name}] - {c.message}")
```

### Output JSON format string (feature of [DefaultProcessor](https://github.com/taizan-hokuto/pytchat/wiki/DefaultProcessor))

```python
import pytchat
import time

chat = pytchat.create(video_id="uIx8l2xlYVY")

while chat.is_alive():
    print(chat.get().json())
    time.sleep(5)

    """
    Each chat item can also be exported individually as JSON.
    for c in chat.get().items:
        print(c.json())
    """
```

### Other examples

- Fetch chat with a buffer ([LiveChat](https://github.com/taizan-hokuto/pytchat/wiki/LiveChat))
- Use with asyncio ([LiveChatAsync](https://github.com/taizan-hokuto/pytchat/wiki/LiveChatAsync))
- YouTube API-compatible chat processor ([CompatibleProcessor](https://github.com/taizan-hokuto/pytchat/wiki/CompatibleProcessor))

## Default Processor Structure

Each chat item can be retrieved using the `sync_items()` function.

<table>
  <tr>
    <th>Name</th>
    <th>Type</th>
    <th>Description</th>
  </tr>
  <tr>
    <td>type</td>
    <td>str</td>
    <td>"superChat", "textMessage", "superSticker", "newSponsor"</td>
  </tr>
  <tr>
    <td>id</td>
    <td>str</td>
    <td>Chat message ID.</td>
  </tr>
  <tr>
    <td>message</td>
    <td>str</td>
    <td>Message text. Emojis are represented as <code>:(shortcut text):</code>.</td>
  </tr>
  <tr>
    <td>messageEx</td>
    <td>str</td>
    <td>List containing message text and emoji dictionaries (id, text, url).</td>
  </tr>
  <tr>
    <td>timestamp</td>
    <td>int</td>
    <td>Unix timestamp in milliseconds.</td>
  </tr>
  <tr>
    <td>datetime</td>
    <td>str</td>
    <td>Example: "2019-10-10 12:34:56"</td>
  </tr>
  <tr>
    <td>elapsedTime</td>
    <td>str</td>
    <td>Elapsed playback time (Replay only). Example: "1:02:27"</td>
  </tr>
  <tr>
    <td>amountValue</td>
    <td>float</td>
    <td>Example: 1234.0</td>
  </tr>
  <tr>
    <td>amountString</td>
    <td>str</td>
    <td>Example: "$1,234"</td>
  </tr>
  <tr>
    <td>currency</td>
    <td>str</td>
    <td><a href="https://en.wikipedia.org/wiki/ISO_4217">ISO 4217 currency code</a> (e.g. "USD")</td>
  </tr>
  <tr>
    <td>bgColor</td>
    <td>int</td>
    <td>RGB integer value.</td>
  </tr>
  <tr>
    <td>author</td>
    <td>object</td>
    <td>See the structure below.</td>
  </tr>
</table>

### Author Object Structure

<table>
  <tr>
    <th>Name</th>
    <th>Type</th>
    <th>Description</th>
  </tr>
  <tr>
    <td>name</td>
    <td>str</td>
    <td>Author display name.</td>
  </tr>
  <tr>
    <td>channelId</td>
    <td>str</td>
    <td>Author's YouTube channel ID.</td>
  </tr>
  <tr>
    <td>channelUrl</td>
    <td>str</td>
    <td>Author's channel URL.</td>
  </tr>
  <tr>
    <td>imageUrl</td>
    <td>str</td>
    <td>Avatar image URL.</td>
  </tr>
  <tr>
    <td>badgeUrl</td>
    <td>str</td>
    <td>Badge image URL.</td>
  </tr>
  <tr>
    <td>isVerified</td>
    <td>bool</td>
    <td>Whether the author is verified.</td>
  </tr>
  <tr>
    <td>isChatOwner</td>
    <td>bool</td>
    <td>Whether the author owns the stream.</td>
  </tr>
  <tr>
    <td>isChatSponsor</td>
    <td>bool</td>
    <td>Whether the author is a channel member.</td>
  </tr>
  <tr>
    <td>isChatModerator</td>
    <td>bool</td>
    <td>Whether the author is a moderator.</td>
  </tr>
</table>

## License

[![MIT License](http://img.shields.io/badge/license-MIT-blue.svg?style=flat)](LICENSE)
