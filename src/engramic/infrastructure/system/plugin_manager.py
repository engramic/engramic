# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

import ensurepip
import importlib.util
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from importlib.resources import as_file, files
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pluggy
import tomli

from engramic.infrastructure.system.engram_profiles import EngramProfiles

if TYPE_CHECKING:
    from importlib.abc import Traversable

    from engramic.core.host import Host


class ResponseType(Enum):
    SUCCESS = 1
    FAILURE = 0


class PluginManager:
    PLUGIN_DEFAULT_ROOT = 'engramic.resources.plugins'

    @dataclass
    class PluginManagerResponse:
        response: ResponseType
        installed_dependencies: set[str]
        detected_dependencies: set[str]

    def __init__(self, host: Host, profile_name: str, *, ignore_profile: bool = False):
        self.host = host
        self.default_plugin_path: Traversable | None = None
        self.custom_plugin_paths: list[str] = []

        # custom_plugin_paths = os.getenv('CUSTOM_PLUGIN_PATHS')

        # if not custom_plugin_paths:
        #    error = 'CUSTOM_PLUGIN_PATHS environment variable is not set.'
        #    logging.info('CUSTOM_PLUGIN_PATHS environment variable not set.')

        # if custom_plugin_paths:
        #    paths = custom_plugin_paths.split(';')
        #    self.custom_plugin_paths = paths[0]
        #    if len(paths) > 1:
        #        error = 'Multiple plugin paths not currently supported.'
        #        raise ValueError(error)

        self.default_plugin_path = files('engramic.resources.plugins')

        with as_file(self.default_plugin_path) as path:
            if path is None or not os.path.isdir(path):
                file_not_found = f'Plugin directory does not exist: {path}'
                logging.info(file_not_found)

        if profile_name is None and not ignore_profile:
            error = 'Profile name empty'
            raise RuntimeError(error)

        if not ignore_profile:
            """Initialize the host with an empty service list."""
            try:
                self.profiles = EngramProfiles()
                self.set_profile(profile_name)
            except RuntimeError as err:
                error = '[ERROR] Failed to load config.'
                raise RuntimeError(error) from err
            except ValueError as err:
                error = '[ERROR] Invalid config file.'
                raise RuntimeError(error) from err
            else:
                logging.debug('Config loaded successfully')

            self.install_dependencies()
            self.import_plugins()

    def install_dependencies(self) -> PluginManagerResponse:
        """
        Analyzes the given profile and installs missing dependencies.
        """
        current_profile = self.profiles.get_currently_set_profile()

        if current_profile is None:
            error = 'Current profile not set.'
            raise RuntimeError(error)

        dependencies = set()
        installed_dependencies = set()
        detected_dependencies = set()

        if current_profile:
            for row_key, row_value in current_profile.items():
                if row_key in {'type', 'name'}:
                    continue

                for usage in row_value:
                    plugin_name = row_value[usage]
                    dependencies.update(self._get_packages(row_key, plugin_name))

            for dependency in dependencies:
                if not self._is_package_installed(dependency):
                    logging.info('Installing %s...import module: %s', dependency[0], dependency[1])
                    self._install_package(dependency)
                    installed_dependencies.add(dependency[0])
                else:
                    detected_dependencies.add(dependency[0])

        return self.PluginManagerResponse(ResponseType.SUCCESS, installed_dependencies, detected_dependencies)

    def set_profile(self, profile_name: str) -> None:
        self.profiles.set_current_profile(profile_name)

    def import_plugins(self) -> None:
        current_profile = self.profiles.get_currently_set_profile()

        if current_profile and self.default_plugin_path:
            with as_file(self.default_plugin_path) as plugin_root_path:
                for category in current_profile:
                    category_path = plugin_root_path / category
                    if category_path.is_dir():
                        usage = current_profile[category]
                        for items in usage:
                            plugin_entry = usage[items]
                            plugin_name = plugin_entry['name'].lower()

                            plugin_path = category_path / plugin_name
                            plugin_file = plugin_path / f'{plugin_name}.py'
                            module_name = f'{category}.{plugin_name}'
                            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                            if spec is not None and spec.loader is not None:
                                module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(module)
                                sys.modules[module_name] = module

    def get_plugin(self, category: str, usage: str) -> dict[str, Any]:
        if self.profiles is None:
            return None

        profile = self.profiles.get_currently_set_profile()

        if profile and category in profile and usage in profile[category]:
            cat_usage = profile[category][usage]

            if 'name' in cat_usage:
                name = cat_usage['name']
                module_name = name.lower()
                args = profile[category][usage]

                plugin = sys.modules.get(f'{category}.{module_name}')

                plugin_class = getattr(plugin, name, None)

                if not plugin_class:
                    # If it's not found, raise an error
                    runtime_error = f'Class {name} not found in module {category}.{module_name}'
                    raise RuntimeError(runtime_error)

                pm = pluggy.PluginManager(category)

                if profile['name'] == 'mock':
                    pm.register(plugin_class(self.host.mock_data_collector))
                else:
                    pm.register(plugin_class())

                return {'func': pm.hook, 'args': args, 'usage': usage}

        logging.error('Plugin %s.%s failed to load.', category, usage)
        error = 'Plugin failed to load'
        raise RuntimeError(error)

    def _get_packages(self, key: str, plugin_name: dict[str, str]) -> list[tuple[str, Any]]:
        packages: list[tuple[str, Any]] = []
        if self.default_plugin_path:
            plugin_root_dir = self.default_plugin_path / key / plugin_name['name'].lower()

            packages = self._parse_plugin_toml(str(plugin_root_dir))
        return packages

    def _parse_plugin_toml(self, plugin_root_dir: str) -> list[tuple[str, Any]]:
        """
        Loads dependencies from the plugin.toml file.
        """
        plugin_toml_path = Path(plugin_root_dir) / 'plugin.toml'
        if not plugin_toml_path.exists():
            logging.error('%s not found.', plugin_toml_path)
            return []

        try:
            with open(plugin_toml_path, 'rb') as file:
                config = tomli.load(file)
                dependencies = config.get('project', {}).get('dependencies', [])
                import_map = config.get('tool', {}).get('import-map', {})
                result = [(dep, import_map.get(dep, None)) for dep in dependencies if isinstance(dep, str)]

                return result
        except Exception:
            logging.exception('Error reading plugin.toml')
            return []

    def _is_package_installed(self, package: tuple[str, Any]) -> bool:
        """
        Checks if a package is installed.
        """
        try:
            module_name = re.split(r'[=<>!~]+', package[0])[0].strip()

            if package[1] is not None:
                module_name = package[1]
            importlib.import_module(module_name)
        except ModuleNotFoundError:  # More specific than ImportError
            return False
        else:
            return True

    def _ensure_pip_installed(self) -> bool:
        try:
            logging.info('Attempting to install pip using ensurepip...')
            ensurepip.bootstrap()
        except Exception:
            logging.exception('Failed to install pip using ensurepip')
            return False
        else:
            logging.info('pip installed successfully using ensurepip.')
            return True

    def _install_package(self, package: tuple[str, Any]) -> bool:
        """Installs a package using pip and prints the virtual environment information."""
        # Detect virtual environment
        virtual_env = sys.prefix

        if not virtual_env:
            logging.info('No virtual environment detected. Using system Python.')
            pip_executable = shutil.which('pip')  # Fallback to system pip
        else:
            logging.debug('Using virtual environment: %s', virtual_env)

            # Construct the correct path to the pip executable
            if platform.system() == 'Windows':
                pip_executable = os.path.join(virtual_env, 'Scripts', 'pip.exe')
                logging.error('Windows not tested. This may not work.')
            else:  # Linux/macOS (including WSL)
                pip_executable = os.path.join(virtual_env, 'bin', 'pip3')

            if not pip_executable or not os.path.exists(pip_executable):
                ensurepip.bootstrap()

        # Ensure pip_executable is valid
        if not pip_executable or not os.path.exists(pip_executable):
            logging.error('pip not found. Installing now. %s', pip_executable)
            return False  # Return False instead of proceeding with a None value

        logging.debug('Using pip executable: %s', pip_executable)

        try:
            result = subprocess.run(
                [pip_executable, 'install', package[0]],
                check=True,
                capture_output=True,  # Simplifies output capturing
                text=True,
            )
        except subprocess.CalledProcessError as e:
            logging.exception('Failed to install package: %s', e.stderr)
            return False
        else:
            logging.info('Package installed successfully: %s', result.stdout)
            return True
