# imap-archive

Archives emails from an IMAP server as `.eml` files.

By default, fetches from all mailboxes one at a time and only those, which don't exist locally.
That means, on the first run it will get everything, but for subsequent runs only new items.

## Usage

Either set required values in `config.ini` or use the available command line options.

```bash
./archive_mail.py -h
usage: archive_mail.py [-h] [-d DIR] [-s SERVER] [-p PORT] [-u USERNAME] [-pw PASSWORD] [-e EXCLUDE | -i INCLUDE] [-a ALL] [-b]
                       [-bs BATCH_SIZE] [--dry-run]

options:
  -h, --help            show this help message and exit
  -d DIR, --destination-dir DIR
                        directory where mailboxes will be saved to, default: '.'
  -s SERVER, --server SERVER
                        (required) IMAP server (host), default:
  -p PORT, --port PORT  IMAP server port, default: 993
  -u USERNAME, --username USERNAME
                        (required) username for IMAP login, default:
  -pw PASSWORD, --password PASSWORD
                        (required) password for IMAP login, default:
  -e EXCLUDE, --exclude EXCLUDE
                        exclude (case-sensitive, comma-separated) list of mailboxes, e.g. 'Trash,Junk', default:
  -i INCLUDE, --include INCLUDE
                        include (case-sensitive, comma-separated) list of mailboxes, e.g. 'INBOX,Archive', default: all
  -a ALL, --all ALL     fetch all again (in mailbox) and overwrite any existing files, default: false
  -b, --batch           fetch multiple emails at once, determined by -bs / --batch-size, default: true
  -bs BATCH_SIZE, --batch-size BATCH_SIZE
                        how many emails to fetch at once, default: 10
  --dry-run             do not actually write anything, just print, default: false
```

### Examples

```bash
mkdir -p /tmp/email_backup
./archive_mail.py -s imap.domain.com -u username@domain.com -i INBOX -d /tmp/email_backup
Password: 
12:25:31 - will do INBOX
12:25:31 -- 2213 total in INBOX
12:25:31 --- 25 to fetch for INBOX
12:25:32 -- done with INBOX
12:25:32 - done
```

```bash
./archive_mail.py -s imap.domain.com -u username@domain.com -e Sent,Trash
Password: 
12:25:31 - will do INBOX,Archive
12:25:31 -- 2213 total in INBOX
12:25:31 --- 25 to fetch for INBOX
12:25:32 -- done with INBOX
12:25:33 -- 10 total in Archive
12:25:33 --- 1 to fetch for Archive
12:25:33 -- done with Archive
12:25:34 - done
```

```bash
# set values in config.ini
./archive_mail.py
Password: 
...
12:25:34 - done
```