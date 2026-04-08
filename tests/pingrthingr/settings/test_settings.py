import pytest
from pathlib import Path
from unittest.mock import patch, Mock
from json import load as json_load, dumps as json_dumps
from pingrthingr.settings import SettingsManager

base_path = Path(__file__).parent

@pytest.fixture
def default_settings():
    settings_file = base_path / "resources/default_settings.json"
    return json_load(open(settings_file))

class TestSettingsLoadAndSave:
    def test_default_data(self, default_settings):
        # Test default loading of data
        settings_manager = SettingsManager("./nofile.json")
        assert settings_manager._settings.model_dump() == default_settings

    def test_file_not_found(self, tmp_path, default_settings):
        # Test defaults loaded when file is not found
        settings_file = tmp_path / "badfile.json"
        settings_manager = SettingsManager(str(settings_file))
        assert settings_manager._settings.model_dump() == default_settings

    def test_unreadable_file(self, default_settings):
        # Test defaults loaded when file is unreadable
        with patch("pingrthingr.settings.settings.open", side_effect=PermissionError("Permission denied")):
            settings_manager = SettingsManager(str("unreadable.json"))
        assert settings_manager._settings.model_dump() == default_settings

    def test_malformed_file(self, tmp_path, default_settings):
        # Test defaults loaded when file is malformed
        settings_file = tmp_path / "badfile.json"
        settings_file.write_text("not a json file")
        settings_manager = SettingsManager(str(settings_file))
        assert settings_manager._settings.model_dump() == default_settings

    @pytest.mark.parametrize("settings_json", json_load(open(base_path / "resources/invalid_settings.json")))
    def test_invalid_data(self, tmp_path, settings_json, default_settings):
        # Test defaults loaded when file contains invalid data
        settings_file = tmp_path / "badfile.json"
        settings_file.write_text(json_dumps(settings_json))
        settings_manager = SettingsManager(str(settings_file))
        assert settings_manager._settings.model_dump() == default_settings

    def test_valid_data(self):
        # Test loading of valid data
        settings_file = base_path / "resources/valid_settings.json"
        valid_settings = json_load(open(settings_file))
        settings_manager = SettingsManager(str(settings_file))
        assert settings_manager._settings.model_dump() == valid_settings

    def test_save_settings(self, tmp_path):
        # Test saving of settings to file
        settings_file = tmp_path / "settings.json"
        settings_manager = SettingsManager(settings_file)
        settings_manager._settings.display_mode = "Text"
        settings_manager._settings.paused = True
        settings_manager._settings.targets = ["1.2.3.4"]
        settings_manager.save()
        saved_settings = json_load(open(settings_file))
        assert saved_settings == {
            'display_mode': 'Text', 
            'paused': True, 
            'targets': ['1.2.3.4']
        }

class TestSettingsSetGetandCallbacks:
    def test_register_callback(self):
        settings_manager = SettingsManager()
        mock_callback = Mock()
        settings_manager.register_callback("display_mode", mock_callback)
        assert "display_mode" in settings_manager._callbacks
        assert mock_callback in settings_manager._callbacks["display_mode"]

    def test_double_register_callback(self):
        settings_manager = SettingsManager()
        mock_callback = Mock()
        settings_manager.register_callback("display_mode", mock_callback)
        assert mock_callback in settings_manager._callbacks["display_mode"]
        settings_manager.register_callback("display_mode", mock_callback)
        settings_manager.set("display_mode", "Text")
        assert len(settings_manager._callbacks["display_mode"]) == 1, "Callback should not be registered multiple times"
        assert mock_callback.call_count == 1, "Callback should not be registered multiple times"
        settings_manager.deregister_callback("display_mode", mock_callback)  # Deregister once
        settings_manager.set("display_mode", "Dot")
        assert mock_callback.call_count == 1, "Callback should not be called after deregistration"

    def test_set_setting_with_callback(self):
        settings_manager = SettingsManager()
        mock_callback = Mock()
        settings_manager.register_callback("display_mode", mock_callback)
        settings_manager.set("display_mode", "Text")
        assert settings_manager._settings.display_mode == "Text"
        mock_callback.assert_called_once_with("Text")

    def test_deregister_callback(self):
        settings_manager = SettingsManager()
        mock_callback = Mock()
        settings_manager.register_callback("display_mode", mock_callback)
        settings_manager.set("display_mode", "Text")
        assert mock_callback.called, "Callback should have been called when setting was changed"
        settings_manager.deregister_callback("display_mode", mock_callback)
        assert mock_callback not in settings_manager._callbacks.get("display_mode", []), "Callback should have been deregistered"
        settings_manager.set("display_mode", "Dot")
        assert mock_callback.call_count == 1, "Callback should not have been called after deregistration"

    def test_set_get(self):
        settings_manager = SettingsManager()
        assert settings_manager.get("paused") == False
        settings_manager.set("paused", True)
        assert settings_manager.get("paused") == True

    def test_set_invalid_setting(self):
        settings_manager = SettingsManager()
        with pytest.raises(AttributeError):
            settings_manager.set("invalid_setting", "value")

    def test_get_invalid_setting(self):
        settings_manager = SettingsManager()
        with pytest.raises(AttributeError):
            settings_manager.get("invalid_setting")
                                        