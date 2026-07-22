class ConversationNotFoundError(Exception):
    """Raised when a conversation lookup finds nothing, or the requester isn't a participant."""


class NotAParticipantError(Exception):
    """Raised when a user tries to read/send in a conversation they don't belong to."""
