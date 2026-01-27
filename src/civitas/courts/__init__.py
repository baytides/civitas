"""Federal court data from Court Listener.

Credits: Court Listener API by Free Law Project (AGPL-3.0)
https://www.courtlistener.com/api/

Provides:
- CourtListenerClient: Access to federal court opinions
- CourtListenerOpinion: Opinion data model
- CourtListenerCase: Case data model
"""

from .client import CourtListenerClient
from .models import CourtListenerCase, CourtListenerOpinion

__all__ = ["CourtListenerClient", "CourtListenerCase", "CourtListenerOpinion"]
