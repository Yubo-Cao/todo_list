import appdirs
from pathlib import Path

author = "Yubo"
description = "A smarter todo-list that integrate StudentVUE."
license = "MIT"
name = "todo"

config_path = Path(appdirs.user_config_dir(name, author))
data_path = Path(appdirs.user_data_dir(name, author))
log_path = Path(appdirs.user_log_dir(name, author))
cache_path = Path(appdirs.user_cache_dir(name, author))
