from ttskit.telegram.factory import AdapterType, check_dependencies, factory


def test_factory_lists_available_adapters():
    adapters = factory.get_available_adapters()
    assert AdapterType.AIOGRAM in adapters
    assert AdapterType.TELEBOT in adapters


def test_check_dependencies_handles_unknown():
    res = check_dependencies("unknown")
    assert res["available"] is False


def test_recommended_adapter_works_with_dependencies_mock(monkeypatch):
    def fake_check(dep):
        return {"available": dep == AdapterType.AIOGRAM}

    monkeypatch.setattr(factory, "check_dependencies", lambda at: fake_check(at))
    recommended = factory.get_recommended_adapter()
    assert recommended == AdapterType.AIOGRAM
