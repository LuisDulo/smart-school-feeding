# Smart School Feeding Management System

A school meal-management platform: parents top up a child's meal balance by M-Pesa, kitchen staff serve meals by QR code or name, and school administrators monitor balances, demand forecasts and suspicious transactions. Machine-learning models forecast daily meal demand, flag at-risk balances and detect anomalous payments.

Capstone project, BSc Informatics and Computer Science, Strathmore University. Partner organisation: Webmasters Kenya.

## Repository structure

| Folder | Responsibility |
|---|---|
| `backend/` | Django REST API (`accounts`, `meals`, `payments`, `forecasting`, `anomalies`, `core`) and its tests in `backend/tests/` |
| `dashboard/` | React web dashboard for school admins, bursars, kitchen staff and the network super admin |
| `mobile/` | React Native (Expo) app for parents and students, plus a kitchen serving screen |
| `ml/` | Training and evaluation scripts, the training dataset in `ml/data/`, and trained models in `ml/models/` |
| `docs/` | Supporting documentation |

## Prerequisites

Python 3.12, Node.js 20+, PostgreSQL, and the Expo Go app (for the mobile app).

## Setup

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows (use source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env           # then edit .env with your database and Daraja values
python manage.py migrate
python manage.py generate_data        # demo school, staff, students, parents
python manage.py seed_extra_schools   # super admin and two more demo schools
python manage.py runserver 0.0.0.0:8000
```

### Dashboard

```bash
cd dashboard
npm install
npm start                        # http://localhost:3000
```

### Mobile app

Set `BASE_URL` in `mobile/src/services/api.js` to your computer's LAN address, then:

```bash
cd mobile
npm install
npx expo start
```

### Phone push notifications (Android)

Parents get a phone notification when their child collects a meal, when a top-up is confirmed or fails, and as a low-balance payment reminder. They can also set a weekly top-up reminder on the phone from Reminder Settings. The backend sends the messages through Expo's push service, which delivers them through Firebase Cloud Messaging.

Remote push does not work in Expo Go on Android (SDK 53 and later), so the app has to be installed as an Expo **development build**. One-time setup:

1. Install the EAS CLI and sign in with a free Expo account: `npm install -g eas-cli`, then `eas login`.
2. In the [Firebase console](https://console.firebase.google.com) create a project and add an **Android app** with the package name `com.luisdulo.smartschoolfeeding` (set in `mobile/app.json`). Download `google-services.json` and put it in `mobile/`.
3. In Firebase go to Project settings, Service accounts, and generate a new private key. Upload that key to Expo with `eas credentials` (Android, then Google Service Account Key for Push Notifications, FCM V1). Never commit this key; the repo ignores common names for it.
4. From `mobile/` run `eas init` to link the project, then build the app: `eas build --platform android --profile development`. Install the APK it produces on the phone.
5. Start Metro with `npx expo start` and open the installed app. It asks for notification permission after login.

Check delivery with the **Expo push notifications tool** at `expo.dev/notifications`, or serve a meal from the dashboard.

Low-balance reminders are sent by a command, which skips weekends and sends at most one reminder per account per day. Run it every weekday morning with Windows Task Scheduler or cron:

```bash
cd backend
python manage.py send_payment_reminders
```

Use `--dry-run` to list who would be reminded and `--force` to run on a weekend. Set `PUSH_ENABLED=False` in `backend/.env` to switch all push sending off.

### M-Pesa callback

Safaricom must reach `POST /api/payments/callback/` over public HTTPS. For local development run `ngrok http 8000`, then put the forwarding URL in `DARAJA_CALLBACK_URL` and its host in `ALLOWED_HOSTS` in `backend/.env`, and restart the backend.

### Machine-learning models

Trained models are committed in `ml/models/`. To retrain, run the scripts from inside `ml/`, for example `python train_xgboost.py` and `python compare_models.py` for the forecasting models. For anomaly detection run `python train_isolation_forest.py`, `python train_local_outlier_factor.py` and then `python compare_anomaly_models.py`, which writes the comparison shown on the super admin Model Comparison page.

Meal-serving anomalies use a separate Isolation Forest: `python train_meal_anomaly_model.py` retrains it from the meal events in the database and writes `meal_anomaly_evaluation.json`, which the Model Comparison page also shows. The database has no labelled meal anomalies, so it is evaluated by injecting synthetic ones into held-out meals. The deployed detector combines the model with explainable rules (a meal outside 06:00-17:00, on a weekend, or at 3x or more of the student's usual cost), because a forest cannot learn to flag night or weekend meals that never appear in its training data.

## Running the tests

```bash
cd backend
python -m pytest
```

## Demo data

`python manage.py populate_recent_activity` backfills meal and top-up activity up to today, and `python manage.py populate_demo_extras` fills credit requests, support issues and forecast history. Run these before a demonstration so the charts are not empty.

**Anomalies.** Every meal served is scored as it happens, and refused attempts to serve past the daily meal limit are logged; repeated refusals for one student (2 or more in a day) or by one member of staff (5 or more) raise a flag. These appear on the Anomaly Flags page under the Meal Serving tab. To score meals already in the database run `python manage.py scan_meal_anomalies --days 30` (add `--dry-run` to preview). For a demonstration, `python manage.py simulate_anomalies` creates a handful of realistic unusual cases (a very large top-up, a burst of top-ups, a 3 a.m. payment, a night meal, a weekend meal, a very expensive meal and repeated refusals) and runs them through the real detectors. It does not change any balance, and `python manage.py simulate_anomalies --cleanup` removes everything it created.

## Configuration and secrets

All configuration is read from `backend/.env`, which is listed in `.gitignore` and is never committed. `backend/.env.example` lists every setting without real values. The demo accounts created by the seed commands exist for local testing only.

## Contribution workflow

1. Open a GitHub issue describing the task and attach it to a milestone.
2. Branch from `main` as `type/<issue-number>-<description>` where type is `feat`, `fix`, `chore` or `docs`.
3. Commit with `type(<issue-number>): short summary`, for example `fix(40): Add login and register rate limiting`.
4. Open a pull request into `main` whose description says `Closes #<issue-number>`, then merge it.

## Licence and access

Academic project submitted for assessment. All rights reserved; the code is publicly viewable but not licensed for reuse.
