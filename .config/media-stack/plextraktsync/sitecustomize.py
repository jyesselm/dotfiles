"""Loaded at Python startup in the plextraktsync container (PYTHONPATH=/patches, see compose.yml).

pytrakt builds users/{name}/... URLs from the display name, but Trakt's slug for a name like
"skullnite_e981ad" is "skullnite-e981ad"; the underscore URL returns an empty list, so ratings never
came down from Trakt and every sync re-sent the Plex ones. Map underscores to hyphens as Trakt does.
"""

import trakt.users

_slugify = trakt.users.slugify
trakt.users.slugify = lambda value: _slugify(value).replace("_", "-")
