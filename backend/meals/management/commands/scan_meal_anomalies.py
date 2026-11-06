from django.core.management.base import BaseCommand, CommandError

from anomalies.meal_detection import scan_events
from meals.models import School


class Command(BaseCommand):
    help = ('Scores recently served meals and raises an anomaly flag for each '
            'unusual one (odd hours, non-school days, a meal far costlier than '
            "the student's usual, or a statistical outlier). Meals that are "
            'already flagged are skipped, so it is safe to re-run. New meals '
            'are scored automatically as they are served; use this to '
            'backfill history.')

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30,
                            help='How many days back to scan (default 30).')
        parser.add_argument('--school', type=int, default=None,
                            help='Only scan this school id (default: all).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Count what would be flagged without saving.')

    def handle(self, *args, **options):
        school = None
        if options['school'] is not None:
            try:
                school = School.objects.get(id=options['school'])
            except School.DoesNotExist:
                raise CommandError(f"No school with id {options['school']}.")
        counts = scan_events(school=school, days=options['days'],
                             dry_run=options['dry_run'])
        verb = 'would flag' if options['dry_run'] else 'flagged'
        self.stdout.write(
            f"Scanned {counts['scanned']} meal(s) from the last "
            f"{options['days']} day(s); {verb} {counts['flagged']}.")
