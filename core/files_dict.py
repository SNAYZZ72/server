"""
File management module for handling files and directories
"""
import os
import json
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

class FilesDict(dict):
    """
    A dictionary-based container for managing files
    
    This class extends the standard dictionary to enforce string keys and values,
    representing filenames and their corresponding content. It provides methods
    to format its contents and to enforce type checks on keys and values.
    """
    
    def __setitem__(self, key: Union[str, Path], value: str):
        """
        Set the content for the given filename, enforcing type checks
        
        Args:
            key: The filename as a key for the content
            value: The content to associate with the filename
            
        Raises:
            TypeError: If the key is not a string or Path, or if the value is not a string
        """
        if not isinstance(key, (str, Path)):
            raise TypeError("Keys must be strings or Path objects")
        if not isinstance(value, str):
            raise TypeError("Values must be strings")
        super().__setitem__(str(key), value)
    
    def to_dict(self) -> Dict[str, str]:
        """
        Convert the files dictionary to a plain dictionary
        
        Returns:
            A plain dictionary with the same keys and values
        """
        return {str(k): v for k, v in self.items()}
    
    def save_to_disk(self, base_path: Union[str, Path]):
        """
        Save all files to disk
        
        Args:
            base_path: Base path to save files to
        """
        base_path = Path(base_path)
        base_path.mkdir(parents=True, exist_ok=True)
        
        for filename, content in self.items():
            file_path = base_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    @classmethod
    def load_from_disk(cls, base_path: Union[str, Path], pattern: str = "*") -> 'FilesDict':
        """
        Load files from disk into a FilesDict
        
        Args:
            base_path: Base path to load files from
            pattern: Glob pattern to match files
            
        Returns:
            FilesDict with loaded files
        """
        base_path = Path(base_path)
        files_dict = cls()
        
        for file_path in base_path.glob(pattern):
            if file_path.is_file():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Store with relative path as key
                    relative_path = file_path.relative_to(base_path)
                    files_dict[str(relative_path)] = content
                except Exception as e:
                    print(f"Error loading file {file_path}: {str(e)}")
        
        return files_dict
    
    def save_metadata(self, metadata_path: Union[str, Path], metadata: Dict[str, Any]):
        """
        Save metadata associated with the files
        
        Args:
            metadata_path: Path to save metadata to
            metadata: Dictionary of metadata to save
        """
        metadata_path = Path(metadata_path)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    
    @classmethod
    def load_metadata(cls, metadata_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load metadata associated with files
        
        Args:
            metadata_path: Path to load metadata from
            
        Returns:
            Dictionary of metadata
        """
        metadata_path = Path(metadata_path)
        
        if not metadata_path.exists():
            return {}
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata from {metadata_path}: {str(e)}")
            return {}