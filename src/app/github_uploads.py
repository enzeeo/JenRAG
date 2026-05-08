from __future__ import annotations

import base64
from dataclasses import dataclass
import json
from urllib import error, parse, request


class GitHubUploadError(RuntimeError):
    """Raised when the GitHub upload workflow fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class PullRequestResult:
    number: int
    html_url: str


class GitHubUploadClient:
    """Small GitHub REST client for upload branches and pull requests."""

    def __init__(
        self,
        repository: str,
        token: str,
        base_branch: str = "main",
        api_base_url: str = "https://api.github.com",
    ) -> None:
        if "/" not in repository:
            raise GitHubUploadError(
                "GitHub repository must use the owner/repo format."
            )

        self.repository = repository
        self.token = token
        self.base_branch = base_branch
        self.api_base_url = api_base_url.rstrip("/")

    def path_exists_on_base_branch(self, repo_path: str) -> bool:
        """Return True when a file already exists on the base branch."""
        encoded_repo_path = quote_repo_path(repo_path)
        request_path = (
            f"/repos/{self.repository}/contents/{encoded_repo_path}"
            f"?ref={parse.quote(self.base_branch)}"
        )

        try:
            self._request_json("GET", request_path)
        except GitHubUploadError as error_instance:
            if error_instance.status_code == 404:
                return False
            raise

        return True

    def create_upload_pull_request(
        self,
        repo_path: str,
        file_bytes: bytes,
        branch_name: str,
        pull_request_title: str,
        pull_request_body: str,
        commit_message: str,
    ) -> PullRequestResult:
        """Create branch, commit upload, then open a pull request."""
        base_branch_sha = self.get_branch_sha(self.base_branch)
        self.create_branch(branch_name, base_branch_sha)
        self.create_file(repo_path, file_bytes, branch_name, commit_message)
        return self.create_pull_request(
            pull_request_title=pull_request_title,
            pull_request_body=pull_request_body,
            branch_name=branch_name,
        )

    def get_branch_sha(self, branch_name: str) -> str:
        """Return the latest commit SHA for a branch."""
        encoded_branch_name = quote_branch_name(branch_name)
        response = self._request_json(
            "GET",
            f"/repos/{self.repository}/git/ref/heads/{encoded_branch_name}",
        )
        return str(response["object"]["sha"])

    def create_branch(self, branch_name: str, sha: str) -> None:
        """Create a new branch from an existing commit SHA."""
        request_body = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha,
        }
        self._request_json(
            "POST",
            f"/repos/{self.repository}/git/refs",
            data=request_body,
        )

    def create_file(
        self,
        repo_path: str,
        file_bytes: bytes,
        branch_name: str,
        commit_message: str,
    ) -> None:
        """Commit a new file into a branch."""
        encoded_repo_path = quote_repo_path(repo_path)
        request_body = {
            "message": commit_message,
            "content": base64.b64encode(file_bytes).decode("ascii"),
            "branch": branch_name,
        }
        self._request_json(
            "PUT",
            f"/repos/{self.repository}/contents/{encoded_repo_path}",
            data=request_body,
        )

    def create_pull_request(
        self,
        pull_request_title: str,
        pull_request_body: str,
        branch_name: str,
    ) -> PullRequestResult:
        """Open a pull request into the configured base branch."""
        request_body = {
            "title": pull_request_title,
            "body": pull_request_body,
            "head": branch_name,
            "base": self.base_branch,
        }
        response = self._request_json(
            "POST",
            f"/repos/{self.repository}/pulls",
            data=request_body,
        )
        return PullRequestResult(
            number=int(response["number"]),
            html_url=str(response["html_url"]),
        )

    def _request_json(
        self,
        method: str,
        request_path: str,
        data: dict | None = None,
    ) -> dict:
        """Send a GitHub API request and return parsed JSON."""
        request_headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "JenRAG Upload Client",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        request_body = None
        if data is not None:
            request_headers["Content-Type"] = "application/json"
            request_body = json.dumps(data).encode("utf-8")

        github_request = request.Request(
            url=f"{self.api_base_url}{request_path}",
            data=request_body,
            headers=request_headers,
            method=method,
        )

        try:
            with request.urlopen(github_request) as response:
                response_body = response.read().decode("utf-8")
        except error.HTTPError as http_error:
            error_body = http_error.read().decode("utf-8", errors="replace")
            accepted_permissions = http_error.headers.get(
                "X-Accepted-GitHub-Permissions"
            )
            message = build_github_error_message(
                status_code=http_error.code,
                error_body=error_body,
                method=method,
                request_path=request_path,
                accepted_permissions=accepted_permissions,
            )
            raise GitHubUploadError(message, status_code=http_error.code) from http_error
        except error.URLError as url_error:
            raise GitHubUploadError(
                f"Could not reach GitHub: {url_error.reason}"
            ) from url_error

        if not response_body:
            return {}

        return json.loads(response_body)


def build_github_error_message(
    status_code: int,
    error_body: str,
    method: str,
    request_path: str,
    accepted_permissions: str | None = None,
) -> str:
    """Return a concise error message from a GitHub API failure."""
    try:
        parsed_error = json.loads(error_body)
    except json.JSONDecodeError:
        return (
            f"GitHub API request failed for {method} {request_path} "
            f"with status {status_code}: {error_body}"
        )

    message = parsed_error.get("message", "Unknown GitHub API error")
    error_message = (
        f"GitHub API request failed for {method} {request_path} "
        f"with status {status_code}: {message}"
    )

    if status_code == 403 and accepted_permissions:
        error_message += f" Required permissions: {accepted_permissions}."

    return error_message


def quote_branch_name(branch_name: str) -> str:
    """Quote branch names while preserving slash separators."""
    return parse.quote(branch_name, safe="/")


def quote_repo_path(repo_path: str) -> str:
    """Quote repo paths while preserving slash separators."""
    return parse.quote(repo_path, safe="/")
