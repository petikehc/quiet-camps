from pydantic_settings import BaseSettings

from quiet_camps.db.config import LOCAL_URL


class Settings(BaseSettings):
    database_url: str = LOCAL_URL
    debug: bool = False
    experiments: bool = False
    # POST /ask reads plain words with Claude on Amazon Bedrock (ADR 0005). Off unless switched
    # on: it costs money and needs AWS credentials. AWS_PROFILE and AWS_REGION are the standard
    # AWS variables; with no profile, the usual AWS credential chain applies.
    ask_enabled: bool = False
    ask_model: str = "anthropic.claude-haiku-5-5"
    aws_region: str = "ap-southeast-2"
    aws_profile: str | None = None
