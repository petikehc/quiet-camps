from quiet_camps.ingest.clean import State
from quiet_camps.ingest.parse import CampNight


def night_warnings(night: CampNight, warnings: list[str] | None = None) -> list[str]:
    """What's missing from one camp-night, added to `warnings`.

    Pass your own list to collect the warnings for a whole file.
    """
    if warnings is None:
        warnings = []

    if night.adults is None:
        warnings.append("no party size")
    if night.postcode is None:
        warnings.append("no postcode")
    if night.state is State.UNKNOWN:
        warnings.append("unknown state")
    return warnings
