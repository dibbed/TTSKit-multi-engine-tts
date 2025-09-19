"""
Perfect coverage tests for SmartRouter.

This module targets specific remaining lines (108-109 in synth_async and 554-555 in filtering)
to achieve complete test coverage through exception scenarios.
"""

from unittest.mock import Mock

import pytest

from ttskit.engines.smart_router import SmartRouter


class TestSmartRouterPerfectCoverage:
    """Tests ensuring perfect coverage in SmartRouter.

    Focuses on async synthesis exceptions and advanced filtering error cases for full line coverage.
    """

    @pytest.mark.asyncio
    async def test_synth_async_registry_engines_keyerror(self):
        """Test KeyError in synth_async registry engines access (lines 108-109).

        Parameters:
            mock_registry (unittest.mock.Mock): Mocked EngineRegistry with KeyError on engines.

        Notes:
            Simulates engine lookup failure in async synthesis, expecting an Exception to be raised.
        """
        mock_registry = Mock()

        mock_registry.get_engine.return_value = None

        mock_engines = Mock()
        mock_engines.__getitem__ = Mock(side_effect=KeyError("Engine not found"))
        mock_registry.engines = mock_engines

        mock_registry.get_available_engines.return_value = ["gtts"]

        smart_router = SmartRouter(mock_registry)

        with pytest.raises(Exception):
            await smart_router.synth_async("test", "en")

    def test_filter_engines_outer_exception_complete(self):
        """Test complete outer exception in _filter_engines_by_requirements (lines 554-555).

        Parameters:
            mock_registry (unittest.mock.Mock): Mocked EngineRegistry with full exception chain.

        Notes:
            Covers comprehensive error handling by raising exceptions in all key access points.
        """
        mock_registry = Mock()

        def meets_requirements_side_effect(name, req):
            raise Exception("Registry meets_requirements error")

        mock_registry.meets_requirements.side_effect = meets_requirements_side_effect

        mock_registry.get_engine.side_effect = Exception("get_engine error")

        mock_engines = Mock()
        mock_engines.__getitem__ = Mock(side_effect=Exception("engines error"))
        mock_registry.engines = mock_engines

        smart_router = SmartRouter(mock_registry)

        engines = ["gtts", "edge"]
        requirements = {"offline": True}

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == []

    def test_filter_engines_outer_exception_with_fallback(self):
        """Test outer exception with fallback behavior in _filter_engines_by_requirements (lines 554-555).

        Parameters:
            mock_registry (unittest.mock.Mock): Mocked EngineRegistry with partial exceptions.

        Notes:
            Tests fallback when some engines pass but overall exceptions lead to empty result.
        """
        mock_registry = Mock()

        def meets_requirements_side_effect(name, req):
            if name == "gtts":
                raise Exception("meets_requirements error")
            return True

        mock_registry.meets_requirements.side_effect = meets_requirements_side_effect

        mock_registry.get_engine.side_effect = Exception("get_engine error")

        mock_engines = Mock()
        mock_engines.__getitem__ = Mock(side_effect=Exception("engines error"))
        mock_registry.engines = mock_engines

        smart_router = SmartRouter(mock_registry)

        engines = ["gtts", "edge"]
        requirements = {"offline": False}

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == []

    def test_filter_engines_outer_exception_complex_scenario(self):
        """Test complex outer exception scenario for _filter_engines_by_requirements (lines 554-555).

        Parameters:
            mock_registry (unittest.mock.Mock): Mocked EngineRegistry raising RuntimeError.

        Notes:
            Evaluates handling of complex runtime errors across multiple engines.
        """
        mock_registry = Mock()

        def meets_requirements_side_effect(name, req):
            raise RuntimeError("Complex error scenario")

        mock_registry.meets_requirements.side_effect = meets_requirements_side_effect

        mock_registry.get_engine.side_effect = Exception("get_engine error")

        mock_engines = Mock()
        mock_engines.__getitem__ = Mock(side_effect=Exception("engines error"))
        mock_registry.engines = mock_engines

        smart_router = SmartRouter(mock_registry)

        engines = ["gtts", "edge", "piper"]
        requirements = {"offline": True}

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == []

    @pytest.mark.asyncio
    async def test_synth_async_registry_engines_exception_detailed(self):
        """Detailed test for exception in synth_async registry engines (lines 108-109).

        Parameters:
            mock_registry (unittest.mock.Mock): Mocked EngineRegistry with general Exception.

        Notes:
            Provides deeper coverage of async engine resolution failures, raising Exception.
        """
        mock_registry = Mock()

        mock_registry.get_engine.return_value = None

        mock_engines = Mock()
        mock_engines.__getitem__ = Mock(side_effect=Exception("Registry engines error"))
        mock_registry.engines = mock_engines

        mock_registry.get_available_engines.return_value = ["gtts", "edge"]

        smart_router = SmartRouter(mock_registry)

        with pytest.raises(Exception):
            await smart_router.synth_async("test", "en")

    def test_filter_engines_outer_exception_edge_case(self):
        """Test edge case outer exception in _filter_engines_by_requirements (lines 554-555).

        Parameters:
            mock_registry (unittest.mock.Mock): Mocked EngineRegistry raising ValueError.

        Notes:
            Covers boundary error in requirements check and access, ensuring empty result.
        """
        mock_registry = Mock()

        def meets_requirements_side_effect(name, req):
            raise ValueError("Edge case error")

        mock_registry.meets_requirements.side_effect = meets_requirements_side_effect

        mock_registry.get_engine.side_effect = Exception("get_engine error")

        mock_engines = Mock()
        mock_engines.__getitem__ = Mock(side_effect=Exception("engines error"))
        mock_registry.engines = mock_engines

        smart_router = SmartRouter(mock_registry)

        engines = ["gtts"]
        requirements = {"offline": False}

        result = smart_router._filter_engines_by_requirements(engines, requirements)

        assert result == []
