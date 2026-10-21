"""Verify the portable image's security boundary without a database service."""

import json
import subprocess
import sys


def run(image, *arguments):
    return subprocess.run(
        ["docker", "run", "--rm", *arguments, image, "python", "-c", SCRIPT],
        capture_output=True,
        text=True,
        check=False,
    )


SCRIPT = (
    "import json; import musicshowwins.settings as s; "
    "print(json.dumps([s.DEBUG, s.SECURE_SSL_REDIRECT, "
    "s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE]))"
)


def main(image):
    for secret in (None, "", "dev-only-insecure-secret-key"):
        arguments = () if secret is None else ("--env", f"SECRET_KEY={secret}")
        result = run(image, *arguments)
        if result.returncode == 0 or "SECRET_KEY must be set" not in result.stderr:
            raise RuntimeError(f"Image accepted an absent/development secret: {result}")
    configured = run(
        image,
        "--env",
        "SECRET_KEY=test-only-ci-production-secret-with-sufficient-entropy",
    )
    if configured.returncode or json.loads(configured.stdout) != [
        False,
        True,
        True,
        True,
    ]:
        raise RuntimeError(f"Image did not enable production security: {configured}")
    development = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--env",
            "DEBUG=1",
            image,
            "python",
            "-c",
            "import musicshowwins.settings as s; assert s.DEBUG",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if development.returncode:
        raise RuntimeError(f"Explicit development configuration failed: {development}")
    print(
        "Production image rejects missing/development secrets; "
        "secure and explicit dev settings pass."
    )


if __name__ == "__main__":
    main(sys.argv[1])
