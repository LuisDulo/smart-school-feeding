from datetime import date

from django.core.management.base import BaseCommand

from meals.models import MealAccount, PushReminderLog
from meals.push import ksh, recipients_for_account, send_push


class Command(BaseCommand):
    help = ('Sends a phone push notification to the family of every student '
            'whose meal balance is low, asking them to top up. Sends at most '
            'one reminder per account per day and skips weekends (no school '
            'meals) unless --force is given. Schedule it once each weekday '
            'morning, e.g. with Windows Task Scheduler or cron.')

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Run on a weekend too.')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='List who would be reminded without sending anything.')

    def handle(self, *args, **options):
        today = date.today()
        if today.weekday() >= 5 and not options['force']:
            self.stdout.write('Weekend: no school meals today, nothing sent. '
                              'Use --force to override.')
            return

        already = set(PushReminderLog.objects.filter(sent_on=today)
                      .values_list('meal_account_id', flat=True))
        accounts = (MealAccount.objects
                    .select_related('student')
                    .prefetch_related('guardians')
                    .filter(balance_cents__lt=10000))  # below KES 100

        due = [a for a in accounts if a.id not in already]
        sent = skipped = 0
        for account in due:
            title = 'Low meal balance'
            body = (f"{account.student.full_name}'s balance is "
                    f"{ksh(account.balance_cents)}, which may not cover the "
                    f"next meal. Top up now.")
            if options['dry_run']:
                self.stdout.write(f'  would remind: {account.student.full_name}'
                                  f' ({ksh(account.balance_cents)})')
                continue
            queued = send_push(
                recipients_for_account(account), title, body,
                {'type': 'reminder', 'meal_account_id': account.id},
                wait=True)
            if queued:
                PushReminderLog.objects.get_or_create(
                    meal_account=account, sent_on=today)
                sent += 1
            else:
                skipped += 1  # nobody linked to this account has a registered phone

        if options['dry_run']:
            self.stdout.write(f'{len(due)} account(s) below KES 100 would be reminded.')
        else:
            self.stdout.write(
                f'Reminders sent for {sent} account(s); '
                f'{skipped} had no registered phone; '
                f'{len(already)} already reminded today.')
