"""Central constants: FRITZ!Box endpoints, limits, file names and env var names."""

LOGIN_PATH = "/login_sid.lua?version=2"
DATA_PATH = "/data.lua"
INVALID_SID = "0000000000000000"
# A FRITZ!Box 7490 needs several seconds per data.lua request.
HTTP_TIMEOUT_SECONDS = 30

# data.lua form of the web UI's blacklist page, captured from FRITZ!OS 7.62.
BLACKLIST_PAGE = "kids_blacklist"
BLACKLIST_LIST_TYPE = "black"
BLACKLIST_SEPARATOR = "\r\n"
UI_LANGUAGE = "de"
APPLY_OK = "ok"

# The FRITZ!Box web UI refuses blacklists longer than this.
MAX_BLACKLIST_ENTRIES = 500
COMMENT_PREFIX = "#"

DEFAULT_CONFIG_FILE = "boxes.json"
DEFAULT_BLACKLIST_FILE = "blacklist.txt"
CONFIG_ENV_VAR = "EASY_FRITZ_CONFIG"
DEFAULT_LOG_LEVEL = "INFO"
