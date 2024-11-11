import json
import os
from logging import Formatter, LogRecord
from typing import Any, overload

from parser.defaults import *


@overload
def int_or_none(value: Any, /) -> int: ...


@overload
def int_or_none(value: None, /) -> None: ...


def int_or_none(value: Any | None, /) -> int | None:
    """
    Coverts a value to an integer.
    If the passed value is ``None``, returns ``None``.
    """
    return None if value is None else int(value)


class YCFormatter(Formatter):
    """
    Log formatter for Yandex Cloud.
    """
    __slots__ = ()

    def format(self, record: LogRecord, /) -> str:
        message = record.getMessage().rstrip()

        if record.exc_info:
            exc_text = record.exc_text or self.formatException(record.exc_info)
            message = f'{message}\r{exc_text.rstrip()}'

        if record.stack_info:
            stack_text = self.formatStack(record.stack_info)
            message = f'{message}\r{stack_text.rstrip()}'

        message = message.replace('\n', '\r')

        match record.levelname:
            case 'WARNING': level = 'WARN'
            case 'CRITICAL': level = 'FATAL'
            case lvl: level = lvl

        msg = dict(
            msg=message,
            level=level,
            logger=record.name,
            )
        return json.dumps(msg)


def handler(event, context) -> dict[str, Any]:
    """
    Handler for Yandex Cloud function.
    """
    from common.logging import init_logging

    init_logging(formatter=YCFormatter(), use_new_handler=False)

    from parser.update import update_database

    database_uri = os.environ.get('DATABASE_URI')
    skip_rank_update = os.environ.get('SKIP_RANK_UPDATE')
    skip_repo_update = os.environ.get('SKIP_REPO_UPDATE')
    new_repo_limit = os.environ.get('NEW_REPO_LIMIT', DEFAULT_NEW_REPO_LIMIT)
    after_github_id = os.environ.get('NEW_REPO_SINCE', DEFAULT_AFTER_GITHUB_ID)

    update_database(
        database_uri,
        skip_rank_update=bool(skip_rank_update),
        skip_repo_update=bool(skip_repo_update),
        new_repo_limit=int_or_none(new_repo_limit),
        after_github_id=int_or_none(after_github_id),
        )

    return {
        'statusCode':      200,
        'headers':         {
            'Content-Type': 'text/plain'
            },
        'isBase64Encoded': False,
        'body':            'Success',
        }


if __name__ == '__main__':
    def main() -> None:
        import os
        from zipfile import ZipFile

        with ZipFile('cloud-function.zip', 'w') as zf:
            with zf.open('requirements.txt', 'w') as f:
                reqs = [
                    b'psycopg[binary]~=3.2.3',
                    b'pydantic~=2.9.2',
                    ]
                f.write(b'\n'.join(reqs))
                f.write(b'\n')

            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            os.chdir(parent_dir)
            # zf.write(os.path.basename(__file__))
            for parent_path, dirnames, filenames in os.walk('common'):
                for filename in filenames:
                    if filename.endswith('.py'):
                        zf.write(os.path.join(parent_path, filename))

            for parent_path, dirnames, filenames in os.walk('parser'):
                for filename in filenames:
                    if filename.endswith('.py') and filename != '__main__.py':
                        zf.write(os.path.join(parent_path, filename))


    main()
