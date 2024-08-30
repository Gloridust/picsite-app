# config.py
import os
import tempfile

# Git repository configuration
GIT_REPO_URL = 'https://github.com/Gloridust/picsite.git'
GIT_LOCAL_PATH = tempfile.mkdtemp(prefix="picsite_repo_")

# File paths
ALBUMS_PATH = os.path.join(GIT_LOCAL_PATH, 'src', 'content', 'albums')
IMAGES_PATH = os.path.join(GIT_LOCAL_PATH, 'public', 'images')

# Git credentials
GIT_USER = 'yourusername'
GIT_TOKEN = 'yourtoken'
