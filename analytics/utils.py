from dateutil.tz import tzlocal, tzutc
from datetime import datetime
from decimal import Decimal
import logging
import numbers

import six
import sys

log = logging.getLogger('segment')


def is_naive(dt):
    """Determines if a given datetime.datetime is naive."""
    return dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None

def total_seconds(delta):
    """Determines total seconds with python < 2.7 compat."""
    # http://stackoverflow.com/questions/3694835/python-2-6-5-divide-timedelta-with-timedelta
    return (delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 1e6) / 1e6

def guess_timezone(dt):
    """Attempts to convert a naive datetime to an aware datetime."""
    if is_naive(dt):
        # attempts to guess the datetime.datetime.now() local timezone
        # case, and then defaults to utc
        delta = datetime.now() - dt
        if total_seconds(delta) < 5:
            # this was created using datetime.datetime.now()
            # so we are in the local timezone
            return dt.replace(tzinfo=tzlocal())
        else:
            # at this point, the best we can do is guess UTC
            return dt.replace(tzinfo=tzutc())

    return dt

def clean(item):
    if isinstance(item, Decimal):
        return float(item)
    elif isinstance(item, (six.string_types, bool, numbers.Number, datetime,
                         type(None))):
        return item
    elif isinstance(item, (set, list, tuple)):
        return _clean_list(item)
    elif isinstance(item, dict):
        return _clean_dict(item)
    else:
        return _coerce_unicode(item)

def _clean_list(list_):
    return [clean(item) for item in list_]

def _clean_dict(dict_):
    data = {}
    for k, v in six.iteritems(dict_):
        try:
            data[k] = clean(v)
        except TypeError:
            log.warning(
                'Dictionary values must be serializeable to '
                'JSON "%s" value %s of type %s is unsupported.',
                k, v, type(v),
            )
    return data

def _coerce_unicode(cmplx):
    try:
        item = cmplx.decode("utf-8", "strict")
    except AttributeError as exception:
        item = ":".join(exception)
        item.decode("utf-8", "strict")
        log.warning('Error decoding: %s', item)
        return None
    except:
        raise
    return item


def clean_exit(func):
    # ugly hack to get around
    # atexit's excentricities
    if (sys.version_info > (3, 0)):
        import atexit
        # This prevents exceptions and a messy shutdown when the interpreter is
        # destroyed before the daemon thread finishes execution. However, it
        # is *not* the same as flushing the queue! To guarantee all messages
        # have been delivered, you'll still need to call flush().
        atexit.register(func)
    else:
        sys.exitfunc = func
