import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

TEST_PYPI_INDEX = "https://test.pypi.org/simple"
PYPI_INDEX = "https://pypi.org/simple"


def _run(
    command: list[str],
    *,
    cwd: Path,
    timeout: float = 60,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def smoke_test(
    *,
    wheel_directory: Path | None = None,
    testpypi_version: str | None = None,
) -> None:
    uv_executable = shutil.which("uv")
    if uv_executable is None:
        raise RuntimeError("uv must be available on PATH to install the wheel.")

    if wheel_directory is not None:
        wheels = tuple(wheel_directory.glob("system_meter-*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(
                f"Expected exactly one system-meter wheel in {wheel_directory}, "
                f"found {len(wheels)}."
            )
        install_arguments = [str(wheels[0].resolve())]
        package_label = wheels[0].name
    elif testpypi_version is not None:
        install_arguments = [
            "--index-url",
            TEST_PYPI_INDEX,
            "--extra-index-url",
            PYPI_INDEX,
            "--index-strategy",
            "first-index",
            f"system-meter=={testpypi_version}",
        ]
        package_label = f"system-meter=={testpypi_version} from TestPyPI"
    else:
        raise ValueError("Specify either a wheel directory or a TestPyPI version.")

    with tempfile.TemporaryDirectory(prefix="system-meter-smoke-") as temporary:
        temporary_path = Path(temporary)
        environment_path = temporary_path / "venv"
        working_directory = temporary_path / "working-directory"
        working_directory.mkdir()

        _run(
            [uv_executable, "venv", "--python", sys.executable, str(environment_path)],
            cwd=working_directory,
        )

        environment_python = (
            environment_path / "Scripts" / "python.exe"
            if sys.platform == "win32"
            else environment_path / "bin" / "python"
        )
        scripts_directory = environment_python.parent
        speakup_executable = scripts_directory / (
            "speakup.exe" if sys.platform == "win32" else "speakup"
        )

        install_command = [
            uv_executable,
            "pip",
            "install",
            "--python",
            str(environment_python),
            *install_arguments,
        ]
        for attempt in range(3):
            try:
                _run(install_command, cwd=working_directory, timeout=90)
                break
            except subprocess.CalledProcessError as exc:
                details = exc.stderr.strip() or str(exc)
                candidate_not_found = (
                    testpypi_version is not None
                    and "system-meter" in details.lower()
                    and "not found" in details.lower()
                )
                if not candidate_not_found or attempt == 2:
                    raise RuntimeError(
                        f"Unable to install the package for smoke testing: {details}"
                    ) from exc
                time.sleep(15)

        installed_version = _run(
            [
                str(environment_python),
                "-c",
                "from importlib.metadata import version; print(version('system-meter'))",
            ],
            cwd=working_directory,
        ).stdout.strip()
        if testpypi_version is not None and installed_version != testpypi_version:
            raise RuntimeError(
                f"Installed version {installed_version} does not match "
                f"TestPyPI version {testpypi_version}."
            )

        version_result = _run(
            [str(speakup_executable), "--version"],
            cwd=working_directory,
        )
        if version_result.stdout.strip() != f"speakup {installed_version}":
            raise RuntimeError("Installed speakup --version returned unexpected output.")

        json_result = _run(
            [str(speakup_executable), "--json"],
            cwd=working_directory,
        )
        snapshot = json.loads(json_result.stdout)
        if snapshot.get("schema_version") != 1:
            raise RuntimeError("Installed speakup --json returned an unsupported schema.")

        quiet_result = _run(
            [str(speakup_executable), "--quiet"],
            cwd=working_directory,
        )
        if quiet_result.stdout or quiet_result.stderr:
            raise RuntimeError("Installed speakup --quiet unexpectedly produced output.")

        doctor_result = _run(
            [str(speakup_executable), "doctor"],
            cwd=working_directory,
        )
        if "System Meter Doctor" not in doctor_result.stdout:
            raise RuntimeError("Installed speakup doctor returned an unexpected report.")

        print(f"Installed package smoke tests passed: {package_label}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install a built system-meter wheel in a temporary environment and smoke-test its CLI."
    )
    install_target = parser.add_mutually_exclusive_group(required=True)
    install_target.add_argument(
        "--wheel-dir",
        type=Path,
        help="Directory containing exactly one system-meter wheel.",
    )
    install_target.add_argument(
        "--testpypi-version",
        help="Install this system-meter version from TestPyPI.",
    )
    args = parser.parse_args()
    smoke_test(
        wheel_directory=args.wheel_dir,
        testpypi_version=args.testpypi_version,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
