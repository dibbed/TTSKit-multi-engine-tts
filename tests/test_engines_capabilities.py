"""Tests the capabilities and voice listing functionality for GTTSEngine and EdgeEngine.

This module contains unit tests to verify that these TTS engines correctly report their
supported languages and available voices, ensuring basic integration and availability.
"""

from ttskit.engines.edge_engine import EdgeEngine
from ttskit.engines.gtts_engine import GTTSEngine


def test_gtts_capabilities_and_voices():
    """Tests the capabilities and voice listing for the GTTSEngine.

    This test initializes the engine with English as the default language and verifies
    that it reports a non-empty list of supported languages and at least one available
    voice for English.

    Behavior:
    - Checks that languages is a list with length > 0.
    - Ensures voices for 'en' is a non-empty list.
    """
    eng = GTTSEngine(default_lang="en")
    caps = eng.get_capabilities()
    assert isinstance(caps.languages, list) and len(caps.languages) > 0
    voices = eng.list_voices("en")
    assert isinstance(voices, list) and len(voices) >= 1


def test_edge_capabilities_and_voices():
    """Tests the capabilities and voice listing for the EdgeEngine.

    Similar to the GTTSEngine test, this verifies that the EdgeEngine initializes properly
    and provides supported languages and voices for English.

    Behavior:
    - Confirms languages list is non-empty.
    - Validates that English voices are listed as a non-empty list.
    """
    eng = EdgeEngine(default_lang="en")
    caps = eng.get_capabilities()
    assert isinstance(caps.languages, list) and len(caps.languages) > 0
    voices = eng.list_voices("en")
    assert isinstance(voices, list) and len(voices) >= 1
