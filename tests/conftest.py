import sys
from pathlib import Path

# 将 plugins/trpg 目录加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
