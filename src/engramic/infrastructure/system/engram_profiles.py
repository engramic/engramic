# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

from __future__ import annotations

import logging
import os
import shutil
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

import tomli


class EngramProfiles:
    """
    A minimal TOML reader using Python 3.11+ 'tomllib'.

    - Automatically resolves profiles that are of type 'pointer'
      by following the 'ptr' value to the actual profile.
    """

    DEFAULT_PROFILE_PATH = 'default_engram_profiles.toml'
    LOCAL_PROFILE_PATH = 'engram_profiles.toml'
    ENGRAM_PROFILE_VERSION = 0.1

    def __init__(self) -> None:
        self.currently_set_profile: dict[Any, Any] | None = None

        default_path = files('engramic.resources').joinpath(EngramProfiles.DEFAULT_PROFILE_PATH)

        if not default_path.is_file():
            logging.error('Default TOML file not found: %s', EngramProfiles.DEFAULT_PROFILE_PATH)
            error = 'An engram_profiles.toml file must be located in your resources directory.'
            raise FileNotFoundError(error)

        cwd = os.getcwd()
        local_path = Path(cwd, EngramProfiles.LOCAL_PROFILE_PATH)
        if not local_path.is_file():
            try:
                with as_file(default_path) as resolved_path:
                    shutil.copy(str(resolved_path), local_path)
                    logging.info('Created local config from default: %s', local_path)
            except Exception:
                logging.exception('Failed to copy default to local config.')
                raise

        self._data: dict[str, dict[Any, Any]] = {}

        try:
            with local_path.open('rb') as f:
                self._data = tomli.load(f)
        except FileNotFoundError as err:
            error = f'Config file not found: {local_path}'
            raise RuntimeError(error) from err
        except tomli.TOMLDecodeError as err:
            error = f'Invalid TOML format in {local_path}'
            raise ValueError(error) from err

        version = self._data.get('version')

        if not isinstance(version, float | int):  # Ensure version is a numeric type
            logging.error('Invalid profile version type: %s', type(version))
            error = 'Invalid profile version'
            raise TypeError(error)

        if version != EngramProfiles.ENGRAM_PROFILE_VERSION:
            logging.error(
                'Incompatible profile version: Expected: %s Found: %s', EngramProfiles.ENGRAM_PROFILE_VERSION, version
            )
            raise ValueError

    def set_current_profile(self, name: str) -> None:
        profile = self._get_profile(name)
        self.currently_set_profile = profile

    def get_currently_set_profile(self) -> dict[Any, Any]:
        if self.currently_set_profile is None:
            error = 'No profile is currently set.'
            raise ValueError(error)  # Avoid returning None
        return self.currently_set_profile

    def _get_profile(self, name: str) -> dict[Any, Any]:
        """
        Retrieve a TOML table by name.
        - If the table is of type='pointer', follow its ptr until a real profile is found.
        """
        visited: set[str] = set()
        try:
            ret_profile = self._resolve_profile(name, visited)
        except ValueError as err:
            raise ValueError from err
        except KeyError as err:
            raise KeyError from err

        return ret_profile

    def _resolve_profile(self, name: str, visited: set[str]) -> dict[Any, Any]:
        profile: dict[Any, Any] | None = self._data.get(name)

        if not profile:
            logging.error('No TOML profile found for profile="%s".', name)
            raise KeyError

        if profile.get('type') == 'pointer':
            pointer_target: str | None = profile.get('ptr')
            if not pointer_target:
                logging.error("Pointer profile '%s' does not contain 'ptr' key.", name)
                raise ValueError
            return self._resolve_profile(pointer_target, visited)
        if profile.get('type') != 'profile':
            logging.error(
                "Profile '%s' type must contain 'pointer' or 'type' value. Found %s", name, profile.get('type')
            )
            raise ValueError

        profile['name'] = name
        return profile
