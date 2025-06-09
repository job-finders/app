from flask import Flask

from pydantic import BaseModel, Field
import resend

from src.logger import init_logger
from src.config import config_instance

settings = config_instance().EMAIL_SETTINGS


class EmailModel(BaseModel):
    from_: str | None = Field(default=None)
    to_: str | None = Field(default=None)
    subject_: str
    html_: str


class SendMail:
    """
        Make this more formal
    """

    def __init__(self):
        self._resend = resend
        self._resend.api_key = settings.RESEND.API_KEY
        self.from_: str | None = settings.RESEND.from_
        self.logger = init_logger(self.__class__.__name__)

    def init_app(self, app: Flask):
        pass

    async def send_mail_resend(self, email: EmailModel, direct_send: bool = False):
        
        from src.factories.redis_factory import email_queue
        params = {'from': self.from_ or email.from_, 'to': email.to_, 'subject': email.subject_, 'html': email.html_}
        if direct_send:            
            self._resend.Emails.send(params=params)
        else:
            try:                
                email_queue.send_to_queue(email=params)
            except Exception as e:
                # Log warning and fallback
                self.logger.warning(f"Queue unavailable: {e}, sending directly")
                await self.send_mail_resend(email, direct_send=True)
