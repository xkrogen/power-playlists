
class Constants:

    CONFIG_BASE_DIR = 'config'
    APP_CONFIG_FILE = 'app.yaml'
    USER_CONFIG_DIR = 'user'

    SECURITY_SCOPES = 'playlist-read-collaborative playlist-modify-public playlist-read-private '\
                      'playlist-modify-private user-library-modify user-library-read'

    @staticmethod
    def get_app_config_file():
        return f"{Constants.CONFIG_BASE_DIR}/{Constants.APP_CONFIG_FILE}"

    @staticmethod
    def get_user_config_dir():
        return f"{Constants.CONFIG_BASE_DIR}/{Constants.USER_CONFIG_DIR}"
