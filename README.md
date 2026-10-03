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

### M-Pesa callback

Safaricom must reach `POST /api/payments/callback/` over public HTTPS. For local development run `ngrok http 8000`, then put the forwarding URL in `DARAJA_CALLBACK_URL` and its host in `ALLOWED_HOSTS` in `backend/.env`, and restart the backend.

### Machine-learning models

Trained models are committed in `ml/models/`. To retrain, run the scripts from inside `ml/`, for example `python train_xgboost.py` and `python compare_models.py`.

## Running the tests

```bash
cd backend
python -m pytest
```

## Demo data

`python manage.py populate_recent_activity` backfills meal and top-up activity up to today, and `python manage.py populate_demo_extras` fills credit requests, support issues and forecast history. Run these before a demonstration so the charts are not empty.

## Configuration and secrets

All configuration is read from `backend/.env`, which is listed in `.gitignore` and is never committed. `backend/.env.example` lists every setting without real values. The demo accounts created by the seed commands exist for local testing only.

## Contribution workflow

1. Open a GitHub issue describing the task and attach it to a milestone.
2. Branch from `main` as `type/<issue-number>-<description>` where type is `feat`, `fix`, `chore` or `docs`.
3. Commit with `type(<issue-number>): short summary`, for example `fix(40): Add login and register rate limiting`.
4. Open a pull request into `main` whose description says `Closes #<issue-number>`, then merge it.

## Licence and access

Academic project submitted for assessment. All rights reserved; the code is publicly viewable but not licensed for reuse.
