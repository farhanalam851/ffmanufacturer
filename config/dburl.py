"""Parse DATABASE_URL without choking on special characters in the password."""
from urllib.parse import unquote

from django.core.exceptions import ImproperlyConfigured


def parse_database_url(url):
    url = (url or "").strip().strip('"').strip("'")
    if "://" not in url:
        raise ImproperlyConfigured("DATABASE_URL must look like postgresql://user:password@host:port/dbname")
    if "[YOUR-PASSWORD]" in url or "[YOUR_PASSWORD]" in url.upper():
        raise ImproperlyConfigured("DATABASE_URL still contains the placeholder [YOUR-PASSWORD]. Replace it, brackets included, with your real database password.")
    rest = url.split("://", 1)[1]
    creds, sep, hostpart = rest.rpartition("@")  # the LAST @ separates the password from the host
    if not sep:
        raise ImproperlyConfigured("DATABASE_URL is missing user:password@ before the host name.")
    user, _, password = creds.partition(":")
    hostport, _, path = hostpart.partition("/")
    name = path.split("?", 1)[0] or "postgres"
    host, _, port = hostport.rpartition(":") if ":" in hostport else (hostport, "", "")
    if not host or (port and not port.isdigit()):
        raise ImproperlyConfigured("DATABASE_URL has an invalid host or port. Expected host:port/dbname after the @.")
    return {"USER": unquote(user), "PASSWORD": unquote(password), "HOST": host, "PORT": int(port) if port else 5432, "NAME": name}
