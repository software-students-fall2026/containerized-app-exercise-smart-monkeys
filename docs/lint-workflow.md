# Lint workflow

The existing `lint-free` workflow now uses Python 3.12, matching the initial
Docker target in the team plan. It runs on pushes and pull requests, with
independent matrix jobs for `web-app` and `machine-learning-client`.

Each job installs that subsystem's own `requirements.txt` with pip, checks
installed dependency consistency, then runs Pylint and Black. The requirements
file must include both lint tools along with the subsystem dependencies. The
subsystem owner maintains the versions; the workflow does not install a separate,
potentially conflicting set of ML or web dependencies. Pipenv is no longer used
by this workflow. The ML starter Pipfiles have been removed; the separate course
event logger retains its own Pipenv configuration.

A subsystem with no Python files is explicitly reported as empty and skips the
checks until its code arrives. Once Python files exist, a missing requirements
file, failed dependency installation, Pylint failure or Black failure fails the
job. Pylint checks tracked Python files at both the subsystem root and nested
directories, including tests. Black checks the subsystem directory without
rewriting files.

## Local use

In a Python 3.12 virtual environment, enter the subsystem you are checking:

```bash
python -m pip install -r requirements.txt
python -m pip check
git ls-files -z -- '*.py' | xargs -0 python -m pylint
python -m black --diff --check .
```

Stage new Python files before using the Pylint command locally, so Git lists them.
Do not interpret an empty-subsystem skip as passing application validation.

## Scope

This workflow handles lint only. The separate `web-ci.yml` and `ml-ci.yml`
workflows build their subsystem images and enforce independent 80% coverage
gates. The ML workflow also loads the actual downloaded model. Full worker
runtime and three-service Compose integration remain separate tasks.

## Validation of this change

- Actionlint passed for this workflow (external ShellCheck was not installed).
- The workflow's shell commands were exercised in temporary Git repositories on
  macOS with Python 3.12.16, Black 26.10.1 and Pylint 4.1.4.
- Both subsystem fixtures passed dependency installation, Pylint and Black.
- Missing requirements, root-level and nested code errors, and bad formatting
  each produced the expected failure. Empty-subsystem reporting was also checked.
- These are workflow-command checks using small fixtures, not tests of the actual
  ML model, Flask application, Docker images or a hosted GitHub Actions run.

Reference: [GitHub's Python workflow guide](https://docs.github.com/en/actions/tutorials/build-and-test-code/python).
