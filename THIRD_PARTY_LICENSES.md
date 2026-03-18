# Third-Party Licenses

This repository's original source code is licensed under the MIT License. That
license applies only to this repository's original code and documentation, not
to third-party software used, referenced, or distributed alongside it.

The project depends on third-party components that remain under their own
licenses. When redistributing this project, especially as Docker images or
prebuilt artifacts, you should preserve third-party notices and review the
upstream license terms for the exact versions you ship.

## Core products used by this repository

| Component | Where used | Upstream license |
| --- | --- | --- |
| Kanboard | `docker-compose.yml` service `kanboard` | MIT |
| Gitea | `docker-compose.yml` service `gitea` | MIT |
| Gitea `act_runner` | `docker-compose.yml` service `gitea-actions-runner` | MIT |
| Python | Base runtime and local tooling | PSF License |
| FastAPI | Python dependency | MIT |
| HTTPX | Python dependency | BSD-3-Clause |
| Jinja | Python dependency | BSD-3-Clause |
| Pydantic | Python dependency | MIT |
| pydantic-settings | Python dependency | MIT |
| Uvicorn | Python dependency | BSD-3-Clause |
| pytest | Development dependency | MIT |

## Notes

- The `MIT` license for this repository does not relicense Kanboard, Gitea,
  `act_runner`, Python, or any Python package dependency.
- If you distribute only this repository's source code, `LICENSE` is normally
  sufficient for your original work, while this file provides attribution and
  clarity about embedded dependencies.
- If you distribute container images or bundled artifacts, additional
  third-party software may be present beyond the application dependencies listed
  in `pyproject.toml` and `docker-compose.yml`. In that case, review the image
  contents and include any required notices for the bundled system packages.

## Upstream references

- Kanboard: <https://github.com/kanboard/kanboard>
- Gitea: <https://github.com/go-gitea/gitea>
- Gitea `act_runner`: <https://gitea.com/gitea/act_runner>
- Python: <https://github.com/python/cpython>
- FastAPI: <https://github.com/fastapi/fastapi>
- HTTPX: <https://github.com/encode/httpx>
- Jinja: <https://github.com/pallets/jinja>
- Pydantic: <https://github.com/pydantic/pydantic>
- pydantic-settings: <https://github.com/pydantic/pydantic-settings>
- Uvicorn: <https://github.com/encode/uvicorn>
- pytest: <https://github.com/pytest-dev/pytest>
