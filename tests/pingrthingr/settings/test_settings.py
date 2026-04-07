import pytest
from pathlib import Path
from unittest.mock import patch
from json import load as json_load, dumps as json_dumps
from pingrthingr.settings import SettingsManager

base_path = Path(__file__).parent

class TestSettingsManager:
    def test_default_data(self):
        # Test default loading of data
        settings_manager = SettingsManager("./nofile.json")
        assert settings_manager._settings.model_dump() == {'display_mode': 'Dot', 'paused': False, 'targets': []}

    def test_file_not_found(self, tmp_path):
        # Test defaults loaded when file is not found
        settings_file = tmp_path / "badfile.json"
        settings_manager = SettingsManager(str(settings_file))
        assert settings_manager._settings.model_dump() == {'display_mode': 'Dot', 'paused': False, 'targets': []}

    def test_unreadable_file(self):
        # Test defaults loaded when file is unreadable
        with patch("pingrthingr.settings.settings.open", side_effect=PermissionError("Permission denied")):
            settings_manager = SettingsManager(str("unreadable.json"))
        assert settings_manager._settings.model_dump() == {'display_mode': 'Dot', 'paused': False, 'targets': []}

    def test_malformed_file(self, tmp_path):
        # Test defaults loaded when file is malformed
        settings_file = tmp_path / "badfile.json"
        settings_file.write_text("not a json file")
        settings_manager = SettingsManager(str(settings_file))
        assert settings_manager._settings.model_dump() == {'display_mode': 'Dot', 'paused': False, 'targets': []} 

    @pytest.mark.parametrize("settings_json", json_load(open(base_path / "resources/invalid_settings.json")))
    def test_invalid_data(self, tmp_path, settings_json):
        # Test defaults loaded when file contains invalid data
        settings_file = tmp_path / "badfile.json"
        settings_file.write_text(json_dumps(settings_json))
        settings_manager = SettingsManager(str(settings_file))
        assert settings_manager._settings.model_dump() == {'display_mode': 'Dot', 'paused': False, 'targets': []} 

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
                                        