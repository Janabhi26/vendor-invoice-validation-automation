import json
import os
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


def validate_payload(payload):
    """Validate the local Function URL email payload."""

    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    subject = payload.get("subject")
    recipients = payload.get("recipients")
    from_email = payload.get("from_email")
    text = payload.get("text")
    html = payload.get("html")

    if not subject:
        raise ValueError("Missing required field: subject.")

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

    message["To"] = ", ".join(recipients)

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
        exist_ok=True
    )

    file_path = os.path.join(
        OUTPUT_DIRECTORY,
        "latest_email.eml"
    )

    with open(
        file_path,
        "wb"
    ) as email_file:

        email_file.write(
            bytes(message)
        )

    return file_path


class EmailFunctionHandler(BaseHTTPRequestHandler):
    """Local HTTP endpoint that emulates the Lambda email contract."""

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
            "application/json"
        )

        self.send_header(
            "Content-Length",
            str(len(response))
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
                    "error": "Not found."
                },
            )
            return

        content_length = int(
            self.headers.get(
                "Content-Length",
                "0"
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

            self.send_json_response(
                200,
                {
                    "success": True,
                    "message": (
                        "Email prepared successfully."
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
    """Start the local email Function URL emulator."""

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
