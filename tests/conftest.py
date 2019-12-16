from shapeout2 import settings


def pytest_configure(config):
    """This is ran before all tests"""
    # disable update checking
    settings.SettingsFile().set_bool("check update", False)
    settings.SettingsFile().set_bool("check pgversion", False)
