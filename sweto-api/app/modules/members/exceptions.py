class MemberError(Exception):
    """Base class for gym-member errors."""


class GymMemberNotFoundError(MemberError):
    """The member does not exist in this gym."""


class GymMemberPhoneTakenError(MemberError):
    """Another member of this gym already has the phone number."""


class GymMemberArchivedError(MemberError):
    """The action needs an active member."""


class InvalidMembershipPaymentError(MemberError):
    """A cash payment cannot be recorded as asked."""


class MpesaNotConfiguredError(MemberError):
    """M-Pesa payments are switched off on this server."""


class MpesaPaymentPendingError(MemberError):
    """An M-Pesa prompt for this member is still waiting for an answer."""


class MpesaRequestFailedError(MemberError):
    """M-Pesa refused or didn't answer the payment request."""


class PaymentNotFoundError(MemberError):
    """The payment does not exist in this gym."""
