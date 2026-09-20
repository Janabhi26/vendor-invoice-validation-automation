import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, HTTPServer


HOST = "127.0.0.1"
PORT = 8000

OUTPUT_DIRECTORY = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "data",
        "output",
        "emails",
    )
)


def load_local_env():
    """Load simple KEY=VALUE entries from the project .env file."""

    project_root = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
        )
    )

    env_path = os.path.join(
        project_root,
        ".env",
    )

    if not os.path.exists(env_path):
        return

    with open(
        env_path,
        "r",
        encoding="utf-8",
    ) as env_file:

        for line in env_file:
            line = line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split(
                "=",
                1,
            )

            key = key.strip()
            value = value.strip()

            if (
                len(value) >= 2
                and value[0] == '"'
                and value[-1] == '"'
            ):
                value = value[1:-1]

            if (
                len(value) >= 2
                and value[0] == "'"
                and value[-1] == "'"
            ):
                value = value[1:-1]

            os.environ.setdefault(
                key,
                value,
            )


def validate_payload(payload):
    """Validate the local Function URL email payload."""

    if not isinstance(payload, dict):
        raise ValueError(
            "Request body must be a JSON object."
        )

    subject = payload.get("subject")
    recipients = payload.get("recipients")
    from_email = payload.get("from_email")
    text = payload.get("text")
    html = payload.get("html")

    if not subject:
        raise ValueError(
            "Missing required field: subject."
        )

    if not recipients:
        raise ValueError(
            "Missing required field: recipients."
        )

    if not isinstance(recipients, list):
        raise ValueError(
            "recipients must be a list."
        )

    if not from_email:
        raise ValueError(
            "Missing required field: from_email."
        )

    if text is None and html is None:
        raise ValueError(
            "At least one of text or html is required."
        )

    return {
        "subject": str(subject),
        "recipients": recipients,
        "from_email": str(from_email),
        "text": text,
        "html": html,
        "cc": payload.get("cc", []),
        "bcc": payload.get("bcc", []),
    }


def create_email_message(payload):
    """Create an email message from the validated payload."""

    message = EmailMessage()

    message["Subject"] = payload["subject"]
    message["From"] = payload["from_email"]

    recipients = []

    for recipient in payload["recipients"]:

        if isinstance(recipient, str):
            recipients.append(recipient)

        elif isinstance(recipient, dict):

            name = recipient.get("name")
            email = recipient.get("email")

            if not email:
                raise ValueError(
                    "Recipient object must contain an email."
                )

            if name:
                recipients.append(
                    f"{name} <{email}>"
                )
            else:
                recipients.append(email)

        else:
            raise ValueError(
                "Each recipient must be a string or object."
            )

    message["To"] = ", ".join(
        recipients
    )

    if payload["cc"]:
        message["Cc"] = ", ".join(
            str(value)
            for value in payload["cc"]
        )

    if payload["bcc"]:
        message["Bcc"] = ", ".join(
            str(value)
            for value in payload["bcc"]
        )

    if payload["text"] is not None:
        message.set_content(
            str(payload["text"])
        )

    if payload["html"] is not None:

        if payload["text"] is None:
            message.set_content(
                "This email contains HTML content."
            )

        message.add_alternative(
            str(payload["html"]),
            subtype="html",
        )

    return message


def save_email_locally(message):
    """Save the generated email as an .eml file."""

    os.makedirs(
        OUTPUT_DIRECTORY,
        exist_ok=True,
    )

    file_path = os.path.join(
        OUTPUT_DIRECTORY,
        "latest_email.eml",
    )

    with open(
        file_path,
        "wb",
    ) as email_file:

        email_file.write(
            bytes(message)
        )

    return file_path


def send_email_via_gmail(message):
    """Send the email through Gmail SMTP."""

    load_local_env()

    sender = os.environ.get(
        "GMAIL_SENDER"
    )

    app_password = os.environ.get(
        "GMAIL_APP_PASSWORD"
    )

    if app_password:
        app_password = "".join(
            app_password.split()
        )

    if not sender:
        raise ValueError(
            "Missing GMAIL_SENDER in .env."
        )

    if not app_password:
        raise ValueError(
            "Missing GMAIL_APP_PASSWORD in .env."
        )

    context = ssl.create_default_context()

    with smtplib.SMTP(
        "smtp.gmail.com",
        587,
        timeout=30,
    ) as smtp:

        smtp.ehlo()

        smtp.starttls(
            context=context
        )

        smtp.ehlo()

        smtp.login(
            sender,
            app_password,
        )

        smtp.send_message(
            message
        )


class EmailFunctionHandler(BaseHTTPRequestHandler):
    """Local HTTP endpoint that sends validation emails."""

    def send_json_response(
        self,
        status_code,
        body,
    ):
        response = json.dumps(
            body
        ).encode("utf-8")

        self.send_response(
            status_code
        )

        self.send_header(
            "Content-Type",
            "application/json",
        )

        self.send_header(
            "Content-Length",
            str(len(response)),
        )

        self.end_headers()

        self.wfile.write(
            response
        )

    def do_POST(self):
        """Handle POST requests."""

        if self.path != "/":

            self.send_json_response(
                404,
                {
                    "success": False,
                    "error": "Not found.",
                },
            )

            return

        content_length = int(
            self.headers.get(
                "Content-Length",
                "0",
            )
        )

        body = self.rfile.read(
            content_length
        )

        try:

            payload = json.loads(
                body.decode("utf-8")
            )

            validated_payload = validate_payload(
                payload
            )

            message = create_email_message(
                validated_payload
            )

            email_path = save_email_locally(
                message
            )

            send_email_via_gmail(
                message
            )

            self.send_json_response(
                200,
                {
                    "success": True,
                    "message": (
                        "Email sent successfully."
                    ),
                    "email_file": email_path,
                },
            )

        except json.JSONDecodeError:

            self.send_json_response(
                400,
                {
                    "success": False,
                    "error": "Invalid JSON.",
                },
            )

        except ValueError as error:

            self.send_json_response(
                400,
                {
                    "success": False,
                    "error": str(error),
                },
            )

        except smtplib.SMTPAuthenticationError:

            self.send_json_response(
                502,
                {
                    "success": False,
                    "error": (
                        "Gmail authentication failed. "
                        "Check GMAIL_SENDER and "
                        "GMAIL_APP_PASSWORD."
                    ),
                },
            )

        except smtplib.SMTPException as error:

            self.send_json_response(
                502,
                {
                    "success": False,
                    "error": (
                        f"Gmail SMTP error: {error}"
                    ),
                },
            )

        except Exception as error:

            self.send_json_response(
                500,
                {
                    "success": False,
                    "error": str(error),
                },
            )

    def log_message(
        self,
        format_string,
        *args,
    ):
        """Keep local server logs concise."""

        print(
            f"[LOCAL FUNCTION] "
            f"{format_string % args}"
        )


def main():
    """Start the local email Function URL."""

    load_local_env()

    server = HTTPServer(
        (HOST, PORT),
        EmailFunctionHandler,
    )

    print()
    print("=" * 64)
    print("LOCAL EMAIL FUNCTION")
    print("=" * 64)
    print()
    print(
        f"Function URL: "
        f"http://{HOST}:{PORT}/"
    )
    print()
    print(
        "Gmail SMTP delivery: ENABLED"
    )
    print()
    print(
        "Waiting for POST requests..."
    )
    print(
        "Press Ctrl+C to stop."
    )
    print()

    try:

        server.serve_forever()

    except KeyboardInterrupt:

        print()
        print(
            "Stopping local email function..."
        )

    finally:

        server.server_close()


if __name__ == "__main__":
    main()
