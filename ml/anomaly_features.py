"""
Shared data loading for the anomaly-detection scripts.

Builds the per-transaction feature table (amount, time-of-day, activity
counts, deviation from the account's usual amount, days since last
transaction) from the PaymentTransaction table, plus the synthetic
`is_anomaly` label that is used ONLY to evaluate the unsupervised models.
Both train_isolation_forest.py and train_local_outlier_factor.py (and
compare_anomaly_models.py) import from here so every model sees identical data.
"""
import os
import sys

import pandas as pd

FEATURES = [
    'amount_cents',
    'hour_of_day',
    'day_of_week',
    'tx_count_today',
    'tx_count_week',
    'amount_deviation',
    'days_since_last_tx',
]


def load_feature_frame():
    """Return the feature DataFrame (one row per transaction)."""
    import django
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()

    from django.db.models import Avg
    from meals.models import PaymentTransaction

    print("Loading transaction data from database...")

    # ── Load all transactions ─────────────────────────────────────────
    transactions = PaymentTransaction.objects.select_related(
        'meal_account__student'
    ).order_by('created_at')

    if not transactions.exists():
        print("ERROR: No transactions found. Run generate_data first.")
        sys.exit(1)

    # ── Build feature matrix ──────────────────────────────────────────
    rows = []
    for tx in transactions:
        account_id = tx.meal_account_id
        tx_time = tx.created_at

        # Count transactions for this account today
        tx_date = tx_time.date()
        tx_count_today = PaymentTransaction.objects.filter(
            meal_account_id=account_id,
            created_at__date=tx_date,
            created_at__lt=tx_time
        ).count()

        # Count transactions for this account this week
        week_start = tx_date - pd.Timedelta(days=tx_date.weekday())
        tx_count_week = PaymentTransaction.objects.filter(
            meal_account_id=account_id,
            created_at__date__gte=week_start,
            created_at__lt=tx_time
        ).count()

        # Average amount for this account
        account_txs = PaymentTransaction.objects.filter(
            meal_account_id=account_id,
            created_at__lt=tx_time,
            status='confirmed'
        )
        if account_txs.exists():
            avg_amount = account_txs.aggregate(
                avg=Avg('amount_cents')
            )['avg'] or tx.amount_cents
        else:
            avg_amount = tx.amount_cents

        amount_deviation = abs(tx.amount_cents - avg_amount) / max(avg_amount, 1)

        # Days since last transaction
        prev_tx = PaymentTransaction.objects.filter(
            meal_account_id=account_id,
            created_at__lt=tx_time
        ).order_by('-created_at').first()
        if prev_tx:
            days_since = (tx_time.date() - prev_tx.created_at.date()).days
        else:
            days_since = 30  # new account

        # Is this a synthetic anomaly?
        is_anomaly = (
            tx.callback_payload is not None and
            tx.callback_payload.get('anomalous', False)
        )

        rows.append({
            'tx_id': tx.id,
            'amount_cents': tx.amount_cents,
            'hour_of_day': tx_time.hour,
            'day_of_week': tx_time.weekday(),
            'tx_count_today': tx_count_today,
            'tx_count_week': tx_count_week,
            'amount_deviation': round(amount_deviation, 4),
            'days_since_last_tx': min(days_since, 90),
            'is_anomaly': 1 if is_anomaly else 0,
        })

    df = pd.DataFrame(rows)
    print(f"Loaded {len(df)} transactions")
    print(f"Known anomalies in dataset: {df['is_anomaly'].sum()}")
    print(f"Anomaly rate: {df['is_anomaly'].mean()*100:.2f}%")

    return df
