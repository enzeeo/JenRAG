import unittest

from src.app.github_uploads import build_github_error_message


class GitHubUploadErrorMessageTests(unittest.TestCase):
    def test_unauthorized_error_points_to_upload_token(self) -> None:
        error_message = build_github_error_message(
            status_code=401,
            error_body='{"message":"Bad credentials"}',
            method="GET",
            request_path="/repos/example/repository/contents/data%2Fmd",
        )

        self.assertIn(
            "with status 401: Bad credentials",
            error_message,
        )
        self.assertIn("Check `GITHUB_UPLOAD_TOKEN`", error_message)

    def test_permission_header_is_included_for_personal_access_token_403(self) -> None:
        error_message = build_github_error_message(
            status_code=403,
            error_body='{"message":"Resource not accessible by personal access token"}',
            method="POST",
            request_path="/repos/example/repository/pulls",
            accepted_permissions="pull_requests=write,contents=read",
        )

        self.assertIn(
            "GitHub API request failed for POST /repos/example/repository/pulls "
            "with status 403: Resource not accessible by personal access token",
            error_message,
        )
        self.assertIn(
            "Required permissions: pull_requests=write,contents=read.",
            error_message,
        )

    def test_permission_header_is_omitted_when_missing(self) -> None:
        error_message = build_github_error_message(
            status_code=403,
            error_body='{"message":"Resource not accessible by personal access token"}',
            method="GET",
            request_path="/repos/example/repository/contents/data%2Fmd",
        )

        self.assertEqual(
            error_message,
            "GitHub API request failed for GET "
            "/repos/example/repository/contents/data%2Fmd "
            "with status 403: Resource not accessible by personal access token",
        )

    def test_non_json_body_still_includes_request_context(self) -> None:
        error_message = build_github_error_message(
            status_code=502,
            error_body="bad gateway",
            method="PUT",
            request_path="/repos/example/repository/contents/file.md",
        )

        self.assertEqual(
            error_message,
            "GitHub API request failed for PUT "
            "/repos/example/repository/contents/file.md "
            "with status 502: bad gateway",
        )
