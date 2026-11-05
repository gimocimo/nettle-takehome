from django.conf import settings


def will_retry(exc, attempt):
    """Only errors that declare themselves transient (rate limits, provider outages)
    are retried; anything else, bugs included, fails at once."""
    return bool(getattr(exc, "transient", False)) and attempt < settings.JOBS_MAX_ATTEMPTS


def retry_delay_seconds(attempt):
    return min(settings.JOBS_RETRY_BASE_SECONDS * 2 ** (attempt - 1), 900)
