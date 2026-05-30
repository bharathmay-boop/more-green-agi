import logging
import os

log = logging.getLogger(__name__)


def run() -> None:
    checks = [
        ("anthropic",  _check_anthropic),
        ("fal_ai",     _check_fal),
        ("cloudinary", _check_cloudinary),
        ("meta",       _check_meta),
        ("google",     _check_google),
    ]
    results = {}
    for name, fn in checks:
        try:
            fn()
            results[name] = True
        except Exception as e:
            results[name] = str(e)

    print("\nCredential check results:")
    for name, ok in results.items():
        status = "✓" if ok is True else f"✗  {ok}"
        print(f"  {name:<15} {status}")
    print()

    if not all(v is True for v in results.values()):
        raise SystemExit("One or more credentials failed. Fix them before running the pipeline.")


def _check_anthropic() -> None:
    import anthropic
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=key)
    client.models.list()


def _check_fal() -> None:
    key = os.environ.get("FAL_KEY")
    if not key:
        raise ValueError("FAL_KEY not set")


def _check_cloudinary() -> None:
    import cloudinary
    import cloudinary.api
    name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    api_key = os.environ.get("CLOUDINARY_API_KEY")
    secret = os.environ.get("CLOUDINARY_API_SECRET")
    if not all([name, api_key, secret]):
        raise ValueError("One or more CLOUDINARY_* vars not set")
    cloudinary.config(cloud_name=name, api_key=api_key, api_secret=secret)
    cloudinary.api.ping()


def _check_meta() -> None:
    from utils.meta_auth import validate_meta_token
    validate_meta_token()


def _check_google() -> None:
    key = os.environ.get("GOOGLE_API_KEY")
    sheets_id = os.environ.get("GOOGLE_SHEETS_ID")
    if not key:
        raise ValueError("GOOGLE_API_KEY not set")
    if not sheets_id:
        raise ValueError("GOOGLE_SHEETS_ID not set")
