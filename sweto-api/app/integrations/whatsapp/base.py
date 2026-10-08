from typing import Protocol

from app.integrations.delivery import OTPDeliveryError, OTPSender


class WhatsAppDeliveryError(OTPDeliveryError):
    """Raised by a WhatsApp provider when a code could not be handed over.

    Use a stable ``reason`` such as ``provider_rejected``, ``unauthorized``,
    ``template_rejected`` or ``provider_unavailable``. Never include the code,
    the access token or the full provider response.
    """


class WhatsAppOTPProvider(OTPSender, Protocol):
    """Interface for sending sign-in codes over WhatsApp.

    Rules for the live implementation (WhatsApp Business Platform):
    - Send the code with an approved AUTHENTICATION template, never free-form
      text. The template body is fixed by WhatsApp; the code is passed as the
      template parameter (and to the copy-code button if the template has one).
    - There is no reliable way to check before sending whether a number uses
      WhatsApp, so don't add one. Return normally when the API accepts the
      message; raise WhatsAppDeliveryError when it refuses the request,
      times out or is unreachable.
    - Acceptance is not delivery. A number that isn't on WhatsApp fails
      later, through the message status webhook (error 131026). Handling that
      webhook is separate work and is not part of this method.
    - Never log the code, the access token or the recipient's full number.
    """
