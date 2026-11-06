"""
Phone push notifications through Expo's push service.

The mobile app registers its Expo push token with the backend
(accounts.views.PushTokenView). When something a parent cares about happens
(a meal is collected, a top-up lands, balance runs low) the backend calls
`notify_account`, which looks up the devices of everyone linked to that meal
account and asks Expo to deliver the message via Google's FCM.

Pushing is best-effort: it runs after the database transaction commits and in
a background thread, and any failure is logged and swallowed, so a slow or
unreachable Expo service can never fail a payment callback or a meal serve.
"""
import logging
import threading

import requests
from django.conf import settings
from django.db import close_old_connections, transaction

from .models import DeviceToken

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'
EXPO_BATCH_SIZE = 100          # Expo accepts at most 100 messages per request
EXPO_TIMEOUT_SECONDS = 10
TOKEN_PREFIXES = ('ExponentPushToken[', 'ExpoPushToken[')


def is_valid_token(token):
    return (isinstance(token, str) and len(token) <= 255
            and token.startswith(TOKEN_PREFIXES) and token.endswith(']'))


def recipients_for_account(meal_account):
    """Everyone who should hear about this account: guardians and the student."""
    users = {u.id: u for u in meal_account.guardians.all()}
    users[meal_account.student_id] = meal_account.student
    return list(users.values())


def _post_to_expo(messages):
    """POST one batch to Expo and return its per-message tickets."""
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    if getattr(settings, 'EXPO_ACCESS_TOKEN', ''):
        headers['Authorization'] = f'Bearer {settings.EXPO_ACCESS_TOKEN}'
    response = requests.post(EXPO_PUSH_URL, json=messages, headers=headers,
                             timeout=EXPO_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json().get('data', [])


def _deliver(messages):
    """Send in batches and forget tokens Expo reports as no longer valid."""
    for start in range(0, len(messages), EXPO_BATCH_SIZE):
        batch = messages[start:start + EXPO_BATCH_SIZE]
        try:
            tickets = _post_to_expo(batch)
        except Exception as exc:  # network, 4xx/5xx, bad JSON...
            logger.warning('Push delivery failed: %s', exc)
            continue
        for message, ticket in zip(batch, tickets):
            if ticket.get('status') != 'error':
                continue
            error = (ticket.get('details') or {}).get('error')
            if error == 'DeviceNotRegistered':
                DeviceToken.objects.filter(token=message['to']).delete()
                logger.info('Removed unregistered push token')
            else:
                logger.warning('Push rejected (%s): %s', error,
                               ticket.get('message'))


def _deliver_in_thread(messages):
    try:
        _deliver(messages)
    except Exception:  # never let a worker thread die noisily
        logger.exception('Push worker crashed')
    finally:
        close_old_connections()


def send_push(users, title, body, data=None, wait=False):
    """Push a message to every registered device of `users`.

    Returns how many device messages were queued. With wait=True the call
    blocks until Expo has answered (used by the reminder command, which would
    otherwise exit before its background threads finished)."""
    if not getattr(settings, 'PUSH_ENABLED', True):
        return 0
    tokens = list(
        DeviceToken.objects.filter(user__in=users)
        .values_list('token', flat=True).distinct())
    if not tokens:
        return 0
    messages = [{
        'to': token,
        'title': title,
        'body': body,
        'data': data or {},
        'sound': 'default',
        'channelId': 'default',
        'priority': 'high',
    } for token in tokens]
    if wait or getattr(settings, 'PUSH_SYNC', False):
        _deliver(messages)
    else:
        threading.Thread(target=_deliver_in_thread, args=(messages,),
                         daemon=True).start()
    return len(messages)


def notify_account(meal_account, title, body, data=None):
    """Queue a push for an account's family once the current transaction
    commits (immediately when there is none). Never raises."""
    payload = {'meal_account_id': meal_account.id, **(data or {})}

    def _send():
        try:
            send_push(recipients_for_account(meal_account), title, body, payload)
        except Exception:
            logger.exception('Could not queue push notification')

    try:
        transaction.on_commit(_send)
    except Exception:
        logger.exception('Could not schedule push notification')


def ksh(cents):
    return f'KES {cents / 100:,.2f}'
