import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL, SMTP_HOST, SMTP_PORT

logger = logging.getLogger(__name__)


def send_email(subject, html_body, recipient=None):
    """
    Gmail SMTP(App Password)로 HTML 이메일 발송.

    Gmail 앱 비밀번호 설정:
    1. Google 계정 → 보안 → 2단계 인증 활성화
    2. 보안 → 앱 비밀번호 → 앱 선택(기타) → 생성
    3. 생성된 16자리 비밀번호를 .env 의 GMAIL_APP_PASSWORD 에 입력
    """
    to_addr = recipient or RECIPIENT_EMAIL

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"20-20 Club <{GMAIL_ADDRESS}>"
    msg["To"] = to_addr
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        logger.info(f"이메일 발송 중 → {to_addr}")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to_addr, msg.as_bytes())
        logger.info("이메일 발송 완료")
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Gmail 인증 실패. .env 의 GMAIL_APP_PASSWORD 를 확인하세요.\n"
            "앱 비밀번호는 Google 계정 > 보안 > 앱 비밀번호에서 생성할 수 있습니다."
        )
        raise
    except smtplib.SMTPException as e:
        logger.error(f"SMTP 오류: {e}")
        raise
