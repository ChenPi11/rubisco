# -*- coding: utf-8 -*-
# -*- mode: python -*-
# vi: set ft=python :

# Copyright (C) 2024 The C++ Plus Project.
# This file is part of the cppp-repoutils.
#
# cppp-repoutils is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# cppp-repoutils is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
File utilities.
"""

import atexit
import os
import shutil
import tempfile
from pathlib import Path
from types import TracebackType

from repoutils.config import APP_NAME
from repoutils.lib.exceptions import RUShellExecutionException
from repoutils.lib.l10n import _
from repoutils.lib.log import logger
from repoutils.lib.variable import format_str
from repoutils.shared.ktrigger import IKernelTrigger, call_ktrigger

__all__ = [
    "check_file_exists",
    "rm_recursive",
    "human_readable_size",
    "find_command",
    "TemporaryObject",
]


def check_file_exists(path: Path) -> None:
    """Check if the file exists. If exists, ask UCI to overwrite it.

    Args:
        path (Path): The path to check.

    Raises:
        AssertionError: If the file or directory exists and user choose to
            skip.
    """

    if path.exists():
        call_ktrigger(IKernelTrigger.file_exists, path=path)
        # UCI will raise an exception if user choose to skip.
        rm_recursive(path, strict=True)


def assert_rel_path(path: Path) -> None:
    """Assert that the path is a relative path.

    Args:
        path (Path): The path to assert.

    Raises:
        AssertionError: If the path is not a relative path.
    """

    if path.is_absolute():
        raise AssertionError(
            format_str(
                _("Absolute path '{underline}{path}{reset}' is not allowed."),
                fmt={"path": str(path)},
            )
        )


def rm_recursive(path: Path, strict=False):
    """Remove a file or directory recursively.

    Args:
        path (Path): The path to remove.
        strict (bool): Raise an exception if error occurs.

    Raises:
        OSError: If strict is True and an error occurs.
    """

    path = path.absolute()
    if not path.exists():
        return
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            os.remove(path)
        logger.debug("Removed '%s'.", str(path))
    except OSError as exc:
        if strict:
            raise
        logger.warning("Failed to remove '%s'.", str(path), exc_info=exc)


tempdirs: set[Path] = set()


def new_tempdir(prefix: str = "", suffix: str = "") -> Path:
    """Create temporary directory but do not register it.

    Args:
        suffix (str): The suffix of the temporary directory.

    Returns:
        str: The temporary directory.
    """

    path = Path(
        tempfile.mkdtemp(
            suffix=suffix, prefix=prefix, dir=tempfile.gettempdir()  # noqa: E501
        )
    ).absolute()

    return path


def new_tempfile(prefix: str = "", suffix: str = "") -> Path:
    """Create temporary file but do not register it.

    Args:
        suffix (str): The suffix of the temporary file.

    Returns:
        str: The temporary file.
    """

    path = Path(
        tempfile.mkstemp(
            suffix=suffix, prefix=prefix, dir=tempfile.gettempdir()  # noqa: E501
        )[1]
    ).absolute()

    return path


def register_temp(path: Path) -> None:
    """Register temporary.

    Args:
        path (Path): The path to register.
    """

    tempdirs.add(path)
    logger.debug("Registered temporary object '%s'.", str(path))


def unregister_temp(path: Path) -> None:
    """Unregister temporary.

    Args:
        path (Path): The path to unregister.
    """

    try:
        tempdirs.remove(path)
        logger.debug("Unregistered temporary object '%s'.", str(path))
    except KeyError as exc:
        logger.warning(
            "Temporary object '%s' not found when unregistering.",
            str(path),
            exc_info=exc,
        )


class TemporaryObject:
    """This class is a context manager for temporary files or directories."""

    # Type of the temporary object.
    TYPE_FILE: int = 0
    # Type of the temporary object.
    TYPE_DIRECTORY: int = 1

    __path: Path
    __type: int
    __moved: bool = False

    def __init__(self, temp_type: int, path: Path) -> None:
        """Create a temporary object.

        Args:
            temp_type (int): The type of the temporary object.
                Can be TemporaryObject.TYPE_FILE or
                TemporaryObject.TYPE_DIRECTORY.
            path (Path): The path of the temporary object.
                We will register it for temporary later.
        """

        self.__type = temp_type
        self.__path = path
        register_temp(self.__path)

    def __enter__(self) -> "TemporaryObject":
        """Enter the context manager.

        Returns:
            TemporaryObject: The temporary object path.
        """

        return self

    def __exit__(
        self, exc_type: type, exc_value: Exception, traceback: TracebackType
    ) -> None:
        """Exit the context manager.

        Args:
            exc_type (type): The exception type.
            exc_value (Exception): The exception value.
            traceback (traceback): The traceback.
        """

        self.remove()

    def __str__(self) -> str:
        """Get the string representation of the temporary object.

        Returns:
            str: The string representation of the temporary object.
        """

        return str(self.path)

    def __repr__(self) -> str:
        """Get the string representation of the temporary object.

        Returns:
            str: The string representation of the temporary object.
        """

        return f"TemporaryDirectory({repr(self.path)})"

    def __hash__(self) -> int:
        """Get the hash of the temporary object.

        Returns:
            int: The hash of the temporary object.
        """

        return hash(self.path)

    def __eq__(self, obj: object) -> bool:
        """Compare the temporary object with another object.

        Args:
            obj (object): The object to compare.

        Returns:
            bool: True if the temporary object is equal to the object,
                False otherwise.
        """

        if not isinstance(obj, TemporaryObject):
            return False
        return self.path == obj.path

    def __ne__(self, obj: object) -> bool:
        """Compare the temporary object with another object.

        Args:
            obj (object): The object to compare.

        Returns:
            bool: True if the temporary object is not equal to the object,
                False otherwise.
        """

        return not self == obj

    @property
    def path(self) -> Path:
        """Get the temporary object path.

        Returns:
            Path: The temporary object path.
        """

        return self.__path

    @property
    def temp_type(self) -> int:
        """Get the temporary object type.

        Returns:
            int: The temporary object type.
        """

        return self.__type

    def is_file(self) -> bool:
        """Check if the temporary object is a file.

        Returns:
            bool: True if the temporary object is a file, False otherwise.
        """

        return self.path.is_file()

    def is_dir(self) -> bool:
        """Check if the temporary object is a object.

        Returns:
            bool: True if the temporary object is a object, False otherwise.
        """

        return self.path.is_dir()

    def remove(self) -> None:
        """Remove the temporary object."""

        if self.__moved:
            return
        rm_recursive(self.path)
        self.unregister()

    def unregister(self) -> None:
        """Unregister the temporary object.

        Warning:
            Not recommended to call this method directly.
        """

        if self.__moved:
            return
        unregister_temp(self.path)

    def move(self) -> Path:
        """Move the temporary object to a new location.
            Release the ownership of this temporary object.

        Returns:
            Path: The new location of the temporary object.
        """

        self.unregister()
        self.__moved = True
        return self.path

    @classmethod
    def new_file(
        cls, prefix: str = APP_NAME, suffix: str = ""  # noqa: E501
    ) -> "TemporaryObject":
        """Create a temporary file.

        Args:
            prefix (str, optional): Prefix of the temporary path.
                Defaults to APP_NAME.
            suffix (str, optional): Suffix of the temporary path.
                Defaults to "".

        Returns:
            TemporaryObject: The temporary file.
        """

        return cls(cls.TYPE_FILE, new_tempfile(prefix=prefix, suffix=suffix))

    @classmethod
    def new_directory(
        cls, prefix: str = APP_NAME, suffix: str = ""
    ) -> "TemporaryObject":
        """Create a temporary directory.

        Args:
            prefix (str, optional): Prefix of the temporary path.
                Defaults to APP_NAME.
            suffix (str, optional): Suffix of the temporary path.
                Defaults to "".

        Returns:
            TemporaryObject: The temporary directory.
        """

        return cls(
            cls.TYPE_DIRECTORY, new_tempdir(prefix=prefix, suffix=suffix)  # noqa: E501
        )

    @classmethod
    def register_tempobject(cls, path: Path) -> "TemporaryObject":
        """Register a file or a directory to a temporary object.

        Args:
            path (Path): The path of the object.

        Returns:
            TemporaryObject: Registered temporary object.
        """

        return cls(
            cls.TYPE_DIRECTORY if path.is_dir() else cls.TYPE_FILE, path  # noqa: E501
        )

    @classmethod
    def cleanup(cls) -> None:
        """Clean up all temporary directories."""

        for tempdir in tempdirs:
            rm_recursive(tempdir)
            logger.debug("Unregistered temporary object '%s'.", str(tempdir))
        tempdirs.clear()


def human_readable_size(size: int | float) -> str:
    """Convert size to human readable format.

    Args:
        size (int | float): The size to convert.

    Returns:
        str: The human readable size.
    """

    for unit in ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.2f}{unit}"


def find_command(cmd: str, strict: bool = False) -> str:
    """Find the command in the system.

    Args:
        cmd (str): The command to find.

    Returns:
        str: The command path.
    """

    logger.debug("Checking for command '%s' ...", cmd)

    res = shutil.which(cmd)

    logger.info(
        "Checking for command '%s' ... %s",
        cmd,
        res if res else _("not found."),
    )

    if strict and res is None:
        raise RUShellExecutionException(
            format_str(_("Command '{cmd}' not found."), fmt={"cmd": cmd}),
            retcode=RUShellExecutionException.RETCODE_COMMAND_NOT_FOUND,
        )

    return res if res else cmd


# Register cleanup function.
atexit.register(TemporaryObject.cleanup)

if __name__ == "__main__":
    print(f"{__file__}: {__doc__.strip()}")

    # Test1: Basic usage.
    temp = TemporaryObject.new_file()
    print("Created temporary file:", repr(temp))
    print("tempdirs:", tempdirs)
    assert temp.is_file()
    assert not temp.is_dir()
    assert temp.temp_type == TemporaryObject.TYPE_FILE
    temp.remove()
    print("Removed temporary file:", repr(temp))
    print("tempdirs:", tempdirs)

    temp = TemporaryObject.new_directory()
    print("Created temporary directory:", repr(temp))
    print("tempdirs:", tempdirs)
    assert not temp.is_file()
    assert temp.is_dir()
    assert temp.temp_type == TemporaryObject.TYPE_DIRECTORY
    temp.remove()
    print("Removed temporary directory:", repr(temp))
    print("tempdirs:", tempdirs)

    # Test2: Context manager.
    with TemporaryObject.new_file() as temp:
        print("Created temporary file:", repr(temp))
        print("tempdirs:", tempdirs)
        assert temp.is_file()
        assert not temp.is_dir()
        assert temp.temp_type == TemporaryObject.TYPE_FILE
    print("Removed temporary file:", repr(temp))
    print("tempdirs:", tempdirs)

    with TemporaryObject.new_directory() as temp:
        print("Created temporary directory:", repr(temp))
        print("tempdirs:", tempdirs)
        assert not temp.is_file()
        assert temp.is_dir()
        assert temp.temp_type == TemporaryObject.TYPE_DIRECTORY
    print("Removed temporary directory:", repr(temp))
    print("tempdirs:", tempdirs)

    # Test3: Cleanup.
    temp1 = TemporaryObject.new_file()
    temp2 = TemporaryObject.new_directory()
    temp3 = TemporaryObject.new_file("-PREFIX-", "-SUFFIX-")
    temp4 = TemporaryObject.new_directory("-PREFIX-", "-SUFFIX-")
    print("tempdirs:", tempdirs)
    TemporaryObject.cleanup()
    print("Cleaned up temporary directories.")
    print("tempdirs:", tempdirs)
    assert not temp1.path.exists()
    assert not temp2.path.exists()
    assert not temp3.path.exists()
    assert not temp4.path.exists()

    # Test4: Human readable size.
    assert human_readable_size(1023) == "1023.00B"
    assert human_readable_size(1024) == "1.00KiB"
    assert human_readable_size(1024**2) == "1.00MiB"
    assert human_readable_size(1024**3) == "1.00GiB"
    assert human_readable_size(1024**4) == "1.00TiB"
    assert human_readable_size(1024**5) == "1.00PiB"
    assert human_readable_size(1024**6) == "1.00EiB"
    assert human_readable_size(0) == "0.00B"

    # Test5: Find command.
    assert find_command("whoami") == shutil.which("whoami")
    try:
        find_command("_Not_Exist_Command_", strict=True)
        assert False
    except RUShellExecutionException as exc_:
        assert (
            exc_.retcode == RUShellExecutionException.RETCODE_COMMAND_NOT_FOUND
        )  # noqa: E501
