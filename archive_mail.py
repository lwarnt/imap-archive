#!/usr/bin/env python3
"""Fetch emails from IMAP server and save them as .eml"""
import argparse
import configparser
import email
import imaplib
import re
import ssl
import sys

from getpass import getpass
from os import listdir, remove
from pathlib import Path
from time import sleep, localtime as _now, strftime
from zipfile import ZIP_LZMA, ZipFile as zf

def dir_path(path) -> str:
    if Path(path).exists():
        return str(path)
    else:
        raise argparse.ArgumentTypeError(f"dir: {path} is not a valid path")

def check_response(func, action="") -> 'tuple(str,bytes)':
    try:
        typ, data = func
        assert 'OK' in typ
    except:
        raise RuntimeError(f"{action}: {typ} / {data}")

    return typ, data

def sanitize_string(string) -> 'str | None':
    try: # does not work for every special char, but better than nothing
        string = re.sub(r"utf-[0-9][a-z]|iso-[0-9]+-[0-9][a-z]", "", string, flags=re.IGNORECASE).strip()
        return "".join([c for c in string if c in ("@", "-", "_", ".", " ") or c.isalnum()])[:35]
    except:
        return None

def main(args) -> None:
    now = lambda: strftime("%H:%M:%S", _now())
    included = list(filter(len, args.include.split(",")))
    excluded = list(filter(len, args.exclude.split(",")))
    archive_path = f"{args.dir}/mails.zip"
    if Path(archive_path).exists() and args.zip and args.all:
        remove(archive_path)

    bytify = lambda x: bytes(str(x), 'ascii') if type(x) != bytes else x

    with Connection(args.username, args.password, args.server, args.port) as imap:
        if len(included) > 0 and not args.list_mailboxes:
            mailboxes = included
        else:
            _, _mailboxes = check_response(imap.list(), "list")
            # ('OK', [b'(\\HasNoChildren) "/" INBOX', b'(\\HasNoChildren) "/" Sent', ...])
            mailboxes = [m.decode('utf-8').split()[-1] for m in _mailboxes]
            sleep(0.2)

        print(f"{now()} - got these mailboxes: {','.join(mailboxes)}")
        if args.list_mailboxes:
            return None

        mailboxes = [mb for mb in mailboxes if mb not in excluded]
        print(f"{now()} - will do: {','.join(mailboxes)}")

        for mailbox in mailboxes:
            _, count = check_response(imap.select(mailbox, readonly=True), "select") 
            # ('OK', [b'7'])
            indexes = range(1, int(count[0]) + 1)
            print(f"{now()} -- {len(indexes)} total in {mailbox}")

            path = Path(f"{args.dir}/{mailbox}").absolute().as_posix()
            

            if not args.all: # fetch only, if no file for index exists
                if args.zip:
                    with zf(archive_path, "a") as archive:
                        check_list = [x for x in archive.namelist() if mailbox in x] 

                    check_list = list(map(lambda x: x.split(f"{mailbox}/")[-1], check_list))
                else:
                    Path(path).mkdir(parents=True, exist_ok=True)
                    check_list = listdir(path)

                files = filter(re.compile(r"\d+_").match, check_list)
                ids = list(map(lambda x: int(x.split("_")[0]), files))
                fetch = [i for i in indexes if i not in ids]
            else:
                fetch = indexes

            print(f"{now()} --- {len(fetch)} to fetch for {mailbox}")
            chunks = (fetch[x:x + args.batch_size] for x in range(0, len(fetch), args.batch_size))
            # [range(1,2), range(2,3), ...] if --batch wasn't requested, batch_size will be 1
            batches = (",".join((str(item) for item in chunk)) for chunk in chunks)
            # ['1,2,3,4,5', '6,7']

            for batch in batches:
                try:
                    _, _mails = check_response(imap.fetch(bytify(batch), '(RFC822)'), "fetch")
                    # ('OK', [(b'1 (RFC822 {3642}', b'email header + msg \r\n'), b')'])
                    mails = (m for m in _mails if m not in (b')', b'(', b''))
                    messages = (email.message_from_bytes(mail[1]) for mail in mails) # easier header parsing

                    for msg_id in batch.split(","):
                        message = next(messages)
                        subject = sanitize_string(message['Subject']) or "no_subject"
                        from_addr = sanitize_string(message['From']) or "no_sender"
                        file_name = f"{int(msg_id)}_{from_addr}__{subject}.eml"

                        if not args.dry_run:
                            msg_content = message.as_bytes()

                            if args.zip:
                                with zf(archive_path, mode="a", compression=ZIP_LZMA) as archive:
                                    archive.writestr(f"{mailbox}/{file_name}", msg_content)
                            else:
                                with open(f"{path}/{file_name}", "wb") as f:
                                    f.write(msg_content)
                        else:
                            print("--dry-run: would: ", file_name)

                    sleep(0.2)

                except KeyboardInterrupt:
                    print(f"{now()} - Interrupted.")
                    sys.exit(130)

                except Exception:
                    print(f"{now()} ---- failed to do {batch}")
                    # raise

            check_response(imap.close())
            print(f"{now()} -- done with {mailbox}")

    print(f"{now()} - done")
    return None

class Connection(imaplib.IMAP4_SSL):
    def __init__(self, username, password, host, port):
        self.context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        super().__init__(host=self.host, port=self.port, ssl_context=self.context)
        self.login(self.username, self.password)

def read_config(key):
    try:
        value = config["defaults"][key]
    except:
        value = None

    return value

if __name__ == "__main__":
    config = configparser.ConfigParser(allow_no_value=True)
    try:
        config.read("config.ini")
    except:
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("-d","--destination-dir", dest='dir', type=dir_path, default=read_config("dir") or ".", 
                        help="directory where mailboxes will be saved to, default: '.'")
    parser.add_argument("-s", "--server", dest='server', type=str, default=read_config("server") or "",
                        help="(required) IMAP server (host), default:")
    parser.add_argument("-p", "--port", dest='port', default=read_config("port") or 993, type=str,
                        help="IMAP server port, default: 993")
    parser.add_argument("-u", "--username", dest='username', type=str, default=read_config("username") or "",
                        help="(required) username for IMAP login, default:")
    parser.add_argument("-pw", "--password", dest='password', type=str, default=read_config("password") or "",
                        help="(required) password for IMAP login, default:")
    mgroup = parser.add_mutually_exclusive_group()
    mgroup.add_argument("-e", "--exclude", dest='exclude', type=str, default=read_config("exclude") or "", 
                        help="exclude (case-sensitive, comma-separated) list of mailboxes, e.g. 'Trash,Junk', default:")
    mgroup.add_argument("-i", "--include", dest='include', type=str, default=read_config("include") or "",
                        help="include  (case-sensitive, comma-separated) list of mailboxes, e.g. 'INBOX,Archive', default: all")
    parser.add_argument("-a", "--all", dest='all', action='store_true', default=read_config("all") or False, 
                        help="fetch all again (in mailbox) and overwrite any existing files, default: false")
    parser.add_argument("-b", "--batch", dest='batch', action='store_true', default=read_config("batch") or True, 
                        help="fetch multiple emails at once, determined by -bs / --batch-size, default: true")
    parser.add_argument("-bs", "--batch-size", dest='batch_size', type=int, default=read_config("batch_size") or 10, 
                        help="how many emails to fetch at once, default: 10")
    parser.add_argument("--dry-run", dest='dry_run', action='store_true', 
                        help="do not actually write anything, just print, default: false")
    parser.add_argument("-l", "--list-mailboxes", dest='list_mailboxes', action='store_true', 
                        help="list all available mailboxes on server and exit, default: false")
    parser.add_argument("-z", "--zip", dest='zip', action='store_true', default=read_config("zip") or False,
                        help="zip into archive, default: false")
    args = parser.parse_args()

    if len(args.username) == 0: 
        args.username = getpass("Username: ")
    if len(args.password) == 0:
        args.password = getpass("Password: ")

    if any([len(args.server) == 0, len(args.username) == 0, len(args.password) == 0]):
        parser.error("--server, --username, --password can't be empty")

    if not args.batch:
        args.batch_size = 1

    sys.exit(main(args))