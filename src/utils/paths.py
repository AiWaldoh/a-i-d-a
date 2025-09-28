import os
import sys
from pathlib import Path
import zipfile

def get_project_root() -> Path:
    """Get the project root, handling both normal and zipapp execution"""
    # Check if we're running from a zipapp
    if '.pyz' in __file__ and zipfile.is_zipfile(__file__.split('.pyz')[0] + '.pyz'):
        # Running from zipapp - use the directory containing the .pyz file
        pyz_path = __file__.split('.pyz')[0] + '.pyz'
        return Path(pyz_path).parent
    else:
        # Normal execution - go up from src/utils/paths.py
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        return project_root

def get_absolute_path(relative_path: str) -> Path:
    """Get absolute path, handling both normal and zipapp execution"""
    project_root = get_project_root()
    
    # For zipapp, check if the file exists outside the archive first
    if '.pyz' in __file__:
        external_path = project_root / relative_path
        if external_path.exists():
            return external_path
    
    return project_root / relative_path

def read_config_file(filename: str) -> str:
    """Read a configuration file, handling zipapp execution"""
    # First try to read from external file (for .env, custom configs)
    external_path = get_project_root() / filename
    if external_path.exists():
        return external_path.read_text()
    
    # If running from zipapp, try to read from inside the archive
    if '.pyz' in __file__:
        pyz_path = __file__.split('.pyz')[0] + '.pyz'
        try:
            import zipfile
            with zipfile.ZipFile(pyz_path, 'r') as zf:
                return zf.read(filename).decode('utf-8')
        except:
            pass
    
    # Fallback to normal path
    path = get_absolute_path(filename)
    if path.exists():
        return path.read_text()
    
    raise FileNotFoundError(f"Configuration file not found: {filename}")
