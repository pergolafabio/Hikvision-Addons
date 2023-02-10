from config import loadConfig

def test_loadConfig():
    config = loadConfig()
    assert config is not None