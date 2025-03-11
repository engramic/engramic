# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import logging
from pathlib import Path
from typing import TypedDict

import tomli


class Profile(TypedDict, total=False):  # A TOML profile might have optional fields
    type: str
    ptr: str  # If it's a pointer profile
    # Add other expected fields here if needed


class EngramProfiles:
    """
    A minimal TOML reader using Python 3.11+ 'tomllib'.

    - Automatically resolves profiles that are of type 'pointer'
      by following the 'ptr' value to the actual profile.
    """

    DEFAULT_PROFILE_PATH = 'engram_profiles.toml'
    ENGRAM_PROFILE_VERSION = 1.0

    def __init__(self) -> None:
        self.currently_set_profile = None

        path = Path(EngramProfiles.DEFAULT_PROFILE_PATH)
        if not path.is_file():
            logging.error('TOML file not found: %s', EngramProfiles.DEFAULT_PROFILE_PATH)
            raise FileNotFoundError

        self._data: dict[str, Profile] = {}

        with path.open('rb') as f:
            self._data = tomli.load(f)

        version = self._data.get('version')

        if version != EngramProfiles.ENGRAM_PROFILE_VERSION:
            logging.error('Incompatible profile version: %s %s', EngramProfiles.ENGRAM_PROFILE_VERSION, version)
            raise ValueError

    def set_current_profile(self, name: str) -> None:
        profile = self._get_profile(name)
        self.currently_set_profile = profile

    def get_currently_set_profile(self):
        return self.currently_set_profile

    def _get_profile(self, name: str):
        """
        Retrieve a TOML table by name.
        - If the table is of type='pointer', follow its ptr until a real profile is found.
        """
        visited: set = set()
        return self._resolve_profile(name, visited)

    def _resolve_profile(self, name: str, visited: set[str]) -> Profile:
        profile: Profile | None = self._data.get(name)

        if not profile:
            logging.error('No TOML profile found for key %s', name)
            raise KeyError

        if profile.get('type') == 'pointer':
            pointer_target: str | None = profile.get('ptr')
            if not pointer_target:
                logging.error("Pointer profile '%s' does not contain 'ptr' key.", name)
                raise ValueError
            return self._resolve_profile(pointer_target, visited)

        return profile
