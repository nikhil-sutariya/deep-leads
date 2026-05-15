from datetime import datetime

def format_date(date):
    return date.isoformat()

def get_only_date_year(date):
    desired_format = "%b %d, %Y"
    return date.strftime(desired_format)

def parse_date(date_str: str | None) -> datetime | None:
    return datetime.strptime(date_str, "%Y-%m-%d") if date_str else None
