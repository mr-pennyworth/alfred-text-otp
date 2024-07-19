import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import pytz
from Foundation import NSData, NSUnarchiver
from tzlocal import get_localzone

CHAT_DB_PATH = os.path.expanduser("~/Library/Messages/chat.db")


def parse_text(attributed_body: bytes) -> str:
    """The chat.db doesn't seem to be storing the text directly in the text
    column anymore. Instead, it's storing an attributed string in the
    attributedBody column. This function extracts the text from it.
    """
    data = NSData.dataWithBytes_length_(attributed_body, len(attributed_body))
    return NSUnarchiver.unarchiveObjectWithData_(data).string()


def has_any_word(text: str, words: list) -> bool:
    return any(word in text for word in words)


def extract_code(text: str) -> Optional[str]:
    match = re.search(r'\b[0-9]{4,10}\b', text)
    return match.group(0) if match else None


def has_otp(attributed_body: bytes) -> bool:
    text = parse_text(attributed_body).lower()
    return (extract_code(text) is not None
            and has_any_word(text, ["code", "access", "otp"]))


# Convert macOS timestamp to a human-readable local time format
def convert_timestamp(mac_timestamp):
    # macOS stores timestamps as seconds since 01/01/2001
    mac_epoch_start = datetime(2001, 1, 1, tzinfo=pytz.utc)
    timestamp = (
            mac_epoch_start +
            timedelta(seconds=mac_timestamp / 1000000000)
    )
    gmt_timestamp = timestamp.astimezone(get_localzone())
    return gmt_timestamp.strftime('%d %b %H:%M')


@dataclass
class OTPMessage:
    timestamp: str
    code: str
    text: str

    @property
    def alfred_item(self):
        return {
            "title": self.code,
            "arg": self.code,
            "subtitle": f"[{self.timestamp}] {self.text}",
            "quicklookurl": self.quicklookurl(),
        }

    @property
    def html(self) -> str:
        content = self.text.replace(self.code, f"<mark>{self.code}</mark>")
        return f"""
            <html>
              <head>
                <style>
                    body {{
                        font-family: "SF Pro", sans-serif;
                    }}
                    p {{
                        color: var(--result-text-color);
                        margin-top: 15px;
                        margin-left: 10px;
                        margin-right: 10px;
                        font-size: 1.3em;
                    }}
                </style>
              </head>
              <body>
                <p> {content} </p>
              </body>
            </html>"""

    def quicklookurl(self) -> str:
        html_file_path = f"/tmp/otp-{self.code}.html"
        with open(html_file_path, "w") as html_file:
            html_file.write(self.html)
        return html_file_path


def fetch_recent_otp_messages(db_path: str, limit: int = 9) -> list[OTPMessage]:
    conn = sqlite3.connect(db_path)
    conn.create_function("HAS_OTP", 1, has_otp)
    conn.create_function("TEXT", 1, parse_text)

    query = f"""
    SELECT TEXT(attributedBody) AS text, date
    FROM message
    WHERE HAS_OTP(attributedBody)
    ORDER BY date DESC
    LIMIT {limit}
    """

    cursor = conn.cursor()
    try:
        cursor.execute(query)
        messages = cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"An error occurred: {e}")
        return []

    formatted_messages = [
        OTPMessage(
            timestamp=convert_timestamp(date),
            code=extract_code(text),
            text=text
        )
        for text, date in messages if extract_code(text) is not None
    ]

    conn.close()

    return formatted_messages


def main():
    recent_otp_messages = fetch_recent_otp_messages(CHAT_DB_PATH)
    print(json.dumps({
        "items": [m.alfred_item for m in recent_otp_messages]
    }, indent=2))


if __name__ == "__main__":
    main()
