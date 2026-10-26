# Phase 7 — Packaging, Cross-Platform CI, and Release-Readiness Plan

This document turns Phase 7 of the [project roadmap](../README.md#learning-first-development-plan) into an implementation and testing plan. It prepares System Meter for real users by validating the package and CLI on the declared platforms and by adding a manually approved TestPyPI release path.

**Status:** Planned; scope decisions confirmed. No CI workflow or publishing workflow is implemented yet.

## Goal

Verify that System Meter can be tested, built, installed, and invoked as a package on the supported platforms:

- Windows
- macOS
- Linux

The project declares Python **3.13 or newer**. CI will cover Python 3.13 on all three platforms, plus the newest stable Python supported by the project on Ubuntu. TestPyPI publishing must require explicit manual approval. This phase does not publish to production PyPI.

## Before coding: learn

Study these resources before implementation:

1. [Python Packaging User Guide: Packaging Python Projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/) — build distributions, metadata, and installation.
2. [uv package guide](https://docs.astral.sh/uv/guides/package/) — build and publish projects using the project's package manager.
3. [uv GitHub Actions integration](https://docs.astral.sh/uv/guides/integration/github/) — install uv, cache dependencies, and use locked project environments in CI.
4. [GitHub Actions workflow syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions) — jobs, matrices, permissions, and manual workflows.
5. [PyPA Trusted Publishing](https://docs.pypi.org/trusted-publishers/) and [TestPyPI](https://test.pypi.org/) — understand OIDC publishing and how to verify a test release without storing a long-lived upload token.
6. [psutil platform notes](https://psutil.readthedocs.io/en/latest/) — understand which metrics and behaviors can vary by operating system.

## CI contract

### Platform and interpreter matrix

- Use GitHub Actions with maintained hosted runners for Windows, macOS, and Ubuntu.
- Run the complete unit test suite with Python 3.13 on each OS.
- Add a separate newest-stable-Python job on Ubuntu. Keep the project minimum in the matrix so compatibility with the declared floor is continuously checked.
- Do not claim a Python version or OS is supported solely because the workflow starts; require the tests and package smoke checks to pass.
- Avoid duplicating the full newest-Python matrix across every OS unless evidence later shows platform-specific interpreter issues.

### Reproducible setup and checks

For each matrix entry:

1. Check out the repository and install the selected Python and a pinned or otherwise reproducibly installed uv version.
2. Run `uv sync --locked` so CI fails if `uv.lock` is out of date or inconsistent with `pyproject.toml`.
3. Run the full suite with `uv run python -m unittest discover -s tests`.
4. Build source and wheel distributions with `uv build`.
5. Create an isolated environment, install the built wheel rather than importing the source checkout, and invoke the installed `speakup` entry point.
6. Smoke-test `speakup --version`, `speakup --json` (parse the JSON and verify `schema_version`), `speakup --quiet`, and `speakup doctor`. Use the host runner for real collection, but keep assertions independent of optional device metrics.
7. Confirm the wheel and source archive are produced and can be inspected as expected. Preserve build logs and test failures in CI output.

Watch mode is already covered with mocked time and collection in unit tests. CI should not start an indefinite interactive `watch` process or depend on a real terminal; any subprocess smoke test must be bounded and deterministic.

### Workflow safety and maintenance

- Run CI on pull requests and pushes to the main development branch; allow manual runs for diagnosis.
- Use minimal GitHub token permissions for test/build workflows. These workflows must not publish packages.
- Keep CI commands aligned with the documented local `uv` commands.
- Use workflow concurrency/cancellation only if it does not cancel required release or publishing jobs.
- Do not add a linter or coverage threshold as an unrelated requirement; introduce one only if a future project decision defines its value and maintenance cost.

## Package and support verification

- Confirm `pyproject.toml` metadata, Python requirement, dependencies, license/readme references (where applicable), package discovery, and `speakup` console-script entry point are consistent with the source tree and README.
- Build both sdist and wheel from a clean checkout and install the wheel into an isolated environment.
- Smoke-test the installed entry point outside the repository working directory where practical, to prove the wheel contains the runtime package and dependencies are declared correctly.
- Review the built archive contents for accidental local files, credentials, caches, virtual environments, generated reports, and test-only artifacts.
- Document observed platform limitations, especially metrics that are unavailable or behave differently by OS. Do not promise identical metric availability across platforms.
- Update setup and support documentation to distinguish automated CI evidence from manual testing and hardware-dependent behavior.

## Manually approved TestPyPI path

- Provide a manual GitHub Actions workflow (`workflow_dispatch`) for a **TestPyPI-only** release candidate.
- Require a protected GitHub environment with reviewer approval before the publishing job can run. Approval must be an explicit human action after reviewing the selected version and artifact.
- Prefer PyPI Trusted Publishing/OIDC over a stored upload token. Grant `id-token: write` only to the isolated publishing job; test/build jobs must not receive publishing permissions.
- Build once, validate the exact sdist and wheel, then publish those same artifacts to TestPyPI. Do not rebuild different artifacts after approval.
- Do not publish from pull requests, ordinary pushes, or tag creation alone.
- Do not add a production PyPI publishing workflow, credentials, or automatic release trigger in this phase.
- After an approved upload, verify the TestPyPI project page and install the candidate into a clean environment using TestPyPI as the package index. Confirm `speakup --version` and a JSON smoke check work.
- Document that TestPyPI is a staging check and that installing from it may require access to both TestPyPI and the normal package index for dependencies.

## Testing strategy

### Automated test and build checks

- Run the full unit test suite for every OS/Python matrix entry.
- Assert `uv sync --locked` succeeds; do not regenerate the lockfile inside CI to mask drift.
- Build both distributions on the matrix jobs, or use a dedicated build job whose artifacts are then exercised on all required operating systems. Choose the simplest arrangement that actually validates platform installation.
- Install the built wheel into a fresh environment with dependencies resolved from package metadata; avoid the source checkout shadowing the installed package.
- Run the CLI smoke tests against the installed command:
  - `speakup --version` returns success and a version.
  - `speakup --json` emits one parseable schema-version-1 object.
  - `speakup --quiet` returns success without output when collection succeeds.
  - `speakup doctor` returns success and prints a report.
- Keep these checks tolerant of legitimate platform-dependent optional fields and warnings; assert output contracts, not specific hardware values.
- Add workflow validation only if the chosen YAML validation tooling can run without adding disproportionate dependencies or secrets.

### TestPyPI release-candidate checks

- Verify the manual workflow cannot publish without environment approval.
- Verify the publishing job is the only job with OIDC publishing permission.
- Verify the uploaded files are the already validated build artifacts and the destination is TestPyPI, not production PyPI.
- After publication, install the candidate in a clean environment and run version/JSON smoke checks.
- Confirm that no credentials or tokens are printed or stored in the repository.

### Manual platform verification

Automated CI does not guarantee behavior on every device or terminal. Before making a first-release support claim:

1. Review the successful matrix results for Windows, macOS, and Linux.
2. On at least one available machine per platform, run the default snapshot, JSON output, quiet check, `doctor`, and an interactive `watch` session stopped by Ctrl+C.
3. Record any unavailable metrics or terminal-specific limitations in the support documentation.
4. Verify package installation from the TestPyPI candidate on a clean environment, separately from source-tree execution.
5. Review the release checklist and selected version before any manually approved TestPyPI publication.

## Suggested implementation sequence

1. Read the packaging, uv/GitHub Actions, workflow security, Trusted Publishing, and psutil platform references above.
2. Review package metadata and README claims; settle any necessary metadata/documentation changes before adding CI.
3. Implement the test/build/install/smoke workflow for the agreed OS/Python matrix.
4. Exercise the workflow and fix only failures attributable to the project or workflow; record environmental runner limitations separately.
5. Review built archive contents and verify the installed CLI does not import from the repository checkout.
6. Add the protected, manual TestPyPI publishing workflow with least-privilege OIDC configuration and no production publishing path.
7. Run the complete local suite/build and validate the release candidate using the actual TestPyPI workflow only after the repository's environment protection and trusted-publisher settings are configured.
8. Update the README with the verified CI matrix, support caveats, and package installation instructions, then complete the first-release checklist.

## Acceptance checklist

- [ ] GitHub Actions tests Python 3.13 on Windows, macOS, and Linux.
- [ ] CI tests the newest stable supported Python on Ubuntu as well as the declared minimum.
- [ ] CI uses `uv sync --locked` and runs the full unittest suite.
- [ ] Both sdist and wheel build successfully in CI.
- [ ] The built wheel installs in an isolated environment on each required OS and the installed `speakup` entry point works.
- [ ] Installed CLI smoke checks cover version, JSON schema/output, quiet mode, and doctor without assuming optional metrics exist.
- [ ] Workflow permissions are least-privilege, and ordinary tests/builds cannot publish.
- [ ] A separate manual TestPyPI workflow requires protected-environment approval and uses Trusted Publishing/OIDC.
- [ ] The publishing path uploads the exact validated artifacts to TestPyPI only; no production PyPI path is added.
- [ ] A TestPyPI candidate can be installed in a clean environment and passes the version/JSON smoke checks.
- [ ] Documentation distinguishes CI verification from manual platform/device checks and states known limitations accurately.
- [ ] Archive contents are reviewed and contain no local environments, caches, generated reports, or secrets.

## Deliverable and learning outcome

**Deliverable:** Cross-platform evidence for tests, builds, wheel installation, and CLI entry-point behavior, plus a manually gated TestPyPI candidate process and an evidence-based first-release checklist.

**You will learn:** CI matrices, lockfile enforcement, package distributions, isolated installation testing, runner/platform differences, workflow permissions, OIDC trusted publishing, staging releases, and support claims based on observed results.

## Out of scope for Phase 7

- Automatic publishing to production PyPI.
- Publishing from pull requests, pushes, or tags without an explicit approval gate.
- Claims of identical metric support or behavior on every OS and hardware combination.
- Adding metrics, health thresholds, telemetry, or remote monitoring.
- Adding a linter, coverage target, or release automation tool without a separate project decision.
