"""Broadcast Audio Path must stay under /media or /config (no URLs, no host paths)."""
import os

import pytest
from config import AppConfig
from doorbell import Doorbell, resolve_broadcast_audio_path
from pytest_mock import MockerFixture


@pytest.fixture
def mock_doorbell(mocker: MockerFixture) -> Doorbell:
    sdk = mocker.patch("ctypes.CDLL")
    config = AppConfig.Doorbell(
        name="test", ip="localhost", username="admin", password="password"
    )
    return Doorbell(0, config, sdk)


def test_allows_media_file():
    assert resolve_broadcast_audio_path("/media/doorbell/chime.wav") == os.path.realpath(
        "/media/doorbell/chime.wav"
    )


def test_allows_config_file():
    assert resolve_broadcast_audio_path("/config/www/chime.mp3") == os.path.realpath(
        "/config/www/chime.mp3"
    )


def test_strips_whitespace():
    assert resolve_broadcast_audio_path("  /media/chime.wav  ") == os.path.realpath(
        "/media/chime.wav"
    )


def test_rejects_path_traversal_out_of_media():
    with pytest.raises(ValueError, match="must be under /media or /config"):
        resolve_broadcast_audio_path("/media/../etc/passwd")


def test_rejects_host_path():
    with pytest.raises(ValueError, match="must be under /media or /config"):
        resolve_broadcast_audio_path("/etc/passwd")


def test_rejects_media_prefix_without_separator():
    with pytest.raises(ValueError, match="must be under /media or /config"):
        resolve_broadcast_audio_path("/mediafoo/chime.wav")


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/chime.wav",
        "https://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "FILE:///etc/passwd",
    ],
)
def test_rejects_urls(url):
    with pytest.raises(ValueError, match="not a URL"):
        resolve_broadcast_audio_path(url)


@pytest.mark.parametrize("value", ["", "   ", None])
def test_rejects_empty(value):
    with pytest.raises(ValueError, match="empty"):
        resolve_broadcast_audio_path(value)


def test_rejects_relative_path():
    with pytest.raises(ValueError, match="must be under /media or /config"):
        resolve_broadcast_audio_path("media/chime.wav")


def test_stream_audio_file_rejects_url_without_download(mock_doorbell, mocker):
    mock_doorbell.stop_voice_talk = mocker.Mock()
    mock_doorbell._stream_audio_file("http://evil.example/a.wav")
    mock_doorbell.stop_voice_talk.assert_called()
