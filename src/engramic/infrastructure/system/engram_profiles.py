# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import tomllib
from pathlib import Path

class EngramProfiles:
    """
    A minimal TOML reader using Python 3.11+ 'tomllib'.

    - Automatically resolves profiles that are of type 'pointer'
      by following the 'ptr' value to the actual profile.
    """
    DEFAULT_PROFILE_PATH = "engram_profiles.toml"
    ENGRAM_PROFILE_VERSION = 1.0

    def __init__(self) -> None:
        self.currently_set_profile = None

        path = Path(EngramProfiles.DEFAULT_PROFILE_PATH)
        if not path.is_file():
            raise FileNotFoundError(f"TOML file not found: {EngramProfiles.DEFAULT_PROFILE_PATH}")

        with path.open("rb") as f:
            self._data = tomllib.load(f)

        version = self._data.get("version")
        
        if version != EngramProfiles.ENGRAM_PROFILE_VERSION:
            raise ValueError(f"Incompatible profile version: expected {EngramProfiles.ENGRAM_PROFILE_VERSION}, found {version}")
        
    def set_current_profile(self, name:str):
        profile = self._get_profile(name)
        self.currently_set_profile = profile
        return profile

    def get_currently_set_profile(self):
        return self.currently_set_profile
    
    def get_plugin(self,category:str,usage:str):
        category =self.currently_set_profile.get(category)
        var = 0
        return

    def _get_profile(self, name: str):
        """
        Retrieve a TOML table by name.
        - If the table is of type='pointer', follow its ptr until a real profile is found.
        """
        visited = set()
        return self._resolve_profile(name, visited)

    def _resolve_profile(self, name: str, visited: set):
        """
        Internal helper to recursively resolve pointer profiles.
        Detects cycles to avoid infinite recursion if pointers form a loop.
        """
        if name in visited:
            raise ValueError(f"Detected cyclic pointer reference for profile '{name}'")
        visited.add(name)

        profile = self._data.get(name)
        if not profile:
            raise KeyError(f"No TOML profile found for key '{name}'")

        # If this profile is a pointer, follow its 'ptr' to find the real profile
        if profile.get("type") == "pointer":
            pointer_target = profile.get("ptr")
            if not pointer_target:
                raise ValueError(f"Pointer profile '{name}' does not contain 'ptr' key.")
            return self._resolve_profile(pointer_target, visited)

        # It's a real profile (or something that isn't a pointer), so just return it
        return profile
