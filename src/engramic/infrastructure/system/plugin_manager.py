# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.
from __future__ import annotations

import importlib.util
import logging
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import pluggy
import tomli

from engramic.infrastructure.system.engram_profiles import EngramProfiles


class ResponseType(Enum):
    SUCCESS = 1
    FAILURE = 0


class PluginManager:
    PLUGIN_DEFAULT_ROOT = 'src/engramic/infrastructure/plugins'

    @dataclass
    class PluginManagerResponse:
        response: ResponseType
        installed_dependencies: set[str]
        detected_dependencies: set[str]

    def __init__(self, profile_name: str):
        if profile_name is None:
            error = 'Profile name empty'
            raise RuntimeError(error)

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
            logging.info('[INFO] Config loaded successfully')

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
                if row_key == 'type':
                    continue

                for usage in row_value:
                    plugin_name = row_value[usage]
                    dependencies.update(self._get_packages(row_key, plugin_name))

            for dependency in dependencies:
                if not self._is_package_installed(dependency):
                    self._install_package(dependency)
                    installed_dependencies.add(dependency)
                else:
                    detected_dependencies.add(dependency)

        return self.PluginManagerResponse(ResponseType.SUCCESS, installed_dependencies, detected_dependencies)

    def set_profile(self, profile_name: str) -> None:
        self.profiles.set_current_profile(profile_name)

    def import_plugins(self) -> None:
        current_profile = self.profiles.get_currently_set_profile()

        if current_profile:
            for category in current_profile:
                category_path = os.path.join(self.PLUGIN_DEFAULT_ROOT, category)
                if os.path.isdir(category_path):
                    usage = current_profile[category]
                    for items in usage:
                        plugin_entry = usage[items]
                        plugin_name = plugin_entry['name']

                        plugin_path = os.path.join(category_path, plugin_name)
                        plugin_file = os.path.join(plugin_path, f'{plugin_name}.py')
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
                implementation = cat_usage['name']

                args = profile[category][usage]

                plugin = sys.modules.get(f'{category}.{implementation}')

                if plugin:
                    pm = pluggy.PluginManager(category)
                    pm.register(plugin.Mock())
                    return {'func': pm.hook, 'args': args}

        logging.error('Plugin %s.%s failed to load.', category, usage)
        error = 'Plugin failed to load'
        raise RuntimeError(error)

    def _get_packages(self, key: str, plugin_name: dict[str, str]) -> list[str]:
        system_plugin_root_dir = Path(PluginManager.PLUGIN_DEFAULT_ROOT)
        plugin_root_dir = system_plugin_root_dir / key / plugin_name['name']

        packages = self._parse_plugin_toml(str(plugin_root_dir))
        return packages

    def _parse_plugin_toml(self, plugin_root_dir: str) -> list[str]:
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
                return [dep for dep in dependencies if isinstance(dep, str)]
        except Exception:
            logging.exception('Error reading plugin.toml')
            return []

    def _is_package_installed(self, package: str) -> bool:
        """
        Checks if a package is installed.
        """
        try:
            logging.info('Looking for module in: %s', sys.path)
            importlib.import_module(package)
        except ModuleNotFoundError:  # More specific than ImportError
            return False
        else:
            return True

    def _install_package(self, package: str) -> bool:
        """Installs a package using pip and prints the virtual environment information."""
        # Detect virtual environment
        virtual_env = os.environ.get('VIRTUAL_ENV')

        if not virtual_env:
            logging.info('No virtual environment detected. Using system Python.')
            pip_executable = shutil.which('pip')  # Fallback to system pip
        else:
            logging.info('Using virtual environment: %s', virtual_env)

            # Construct the correct path to the pip executable
            if platform.system() == 'Windows':
                pip_executable = os.path.join(virtual_env, 'Scripts', 'pip.exe')
            else:  # Linux/macOS (including WSL)
                pip_executable = os.path.join(virtual_env, 'bin', 'pip')

            # Handle WSL-specific case (if Windows path is needed)
            if 'microsoft-standard' in platform.uname().release and not os.path.exists(pip_executable):
                try:
                    wsl_path = subprocess.check_output(['/usr/bin/wslpath', '-w', virtual_env]).decode().strip()
                    pip_executable = os.path.join(wsl_path, 'bin', 'pip')
                except FileNotFoundError:
                    logging.warning('wslpath not found. Ensure WSL is installed and accessible.')
                except subprocess.CalledProcessError as e:
                    logging.warning('Failed to execute wslpath: %s', e.output.decode().strip())
                except UnicodeDecodeError:
                    logging.warning('Could not decode wslpath output. Unexpected encoding.')

        # Ensure pip_executable is valid
        if not pip_executable or not os.path.exists(pip_executable):
            logging.error('pip not found. Ensure it is installed and accessible.')
            return False  # Return False instead of proceeding with a None value

        logging.info('Using pip executable: %s', pip_executable)

        try:
            result = subprocess.run(
                [pip_executable, 'install', package],
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
