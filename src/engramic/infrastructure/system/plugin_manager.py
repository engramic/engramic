# Copyright (c) 2025 Preisz Consulting, LLC.
# This file is part of Engramic, licensed under the Engramic Community License.
# See the LICENSE file in the project root for more details.

import importlib
import subprocess
import sys
import tomllib
import os
import shutil
import logging
from  pathlib import Path
from enum import Enum
from dataclasses import dataclass
from typing import List

class ResponseType(Enum):
            SUCCESS = 1
            FAILURE = 0

class PluginManager:
    
    PLUGIN_DEFAULT_ROOT = "src/engramic/infrastructure/plugins"

    

    @dataclass
    class PluginManagerResponse:
        response: ResponseType
        installed_dependencies: List[str]
        detected_dependencies: List[str]
    
    def install_dependencies(self, current_profile: dict) -> PluginManagerResponse:
        """
        Analyzes the given profile and installs missing dependencies.
        """

        dependencies = set()
        for row_key in current_profile:
            if row_key=="type":
                continue
            
            row_value = current_profile[row_key]
            
            if isinstance(row_value, dict):
                for usage in row_value:
                    plugin_name = row_value[usage]
                    dependencies.update(self._get_packages(row_key,plugin_name))
            else:
                plugin_name = row_value
                dependencies.update(self._get_packages(row_key,plugin_name))
            
        installed_dependencies = []
        detected_dependencies = []
        for dependency in dependencies:
            if self._is_package_installed(dependency) != False:
                self._install_package(dependency)
                installed_dependencies.append(dependency)
            else:
                detected_dependencies.append(dependency)

        return self.PluginManagerResponse(
                    ResponseType.SUCCESS,
                    installed_dependencies,
                    detected_dependencies
                )        

    def _get_packages(self, key, plugin_name):
            installed_dependencies = []

            system_plugin_root_dir = Path(PluginManager.PLUGIN_DEFAULT_ROOT)
            plugin_root_dir = system_plugin_root_dir  / key / plugin_name

            packages = self._parse_plugin_toml(plugin_root_dir)
            return packages

    def _parse_plugin_toml(self, plugin_root_dir: str) -> List[str]:
        """
        Loads dependencies from the plugin.toml file.
        """
        plugin_toml_path = Path(plugin_root_dir) / "plugin.toml"
        if not plugin_toml_path.exists():
            logging.error("%s not found.",plugin_toml_path)
            return []

        try:
            with open(plugin_toml_path, "rb") as file:
                config = tomllib.load(file)
                return config.get("project", {}).get("dependencies", [])
        except Exception as e:
            logging.error("Error reading plugin.toml: %s",e)
            return []

    def _is_package_installed(self, package: str) -> bool:
        """
        Checks if a package is installed.
        """
        try:
            importlib.import_module(package)
            return True
        except ImportError:
            return False
    
    def _install_package(self, package: str) -> bool:
        """Installs a package using pip and prints the virtual environment information."""
        # Detect virtual environment
        virtual_env = os.environ.get("VIRTUAL_ENV")
        if not virtual_env:
            print("No virtual environment detected. Using system Python.")
            pip_executable = shutil.which("pip")  # Fallback to system pip
        else:
            print(f"Using virtual environment: {virtual_env}")
            
            # Construct the correct path to the pip executable
            pip_executable = os.path.join(virtual_env, "bin", "pip")  # Linux/macOS
            if not os.path.exists(pip_executable):  # Windows path
                pip_executable = os.path.join(virtual_env, "Scripts", "pip.exe")
            
        # Debugging output
        print("Python Executable:", sys.executable)
        print("Using pip:", pip_executable)

        try:
            subprocess.check_call([pip_executable, "install", package])
            return True
        except subprocess.CalledProcessError:
            return False