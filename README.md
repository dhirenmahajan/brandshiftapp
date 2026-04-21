# BrandShift Cloud Data Analytics


**Live App - https://nice-sky-0f57ad11e.2.azurestaticapps.net**

**University of Cincinnati Cloud Computing Final Project 2026**

End-to-end retail analytics platform built on Azure, analysing the 84.51°/Kroger "Complete Journey 2" sample to answer the brief's retail questions:

- Customer Lifetime Value & high-value segmentation
- Churn / disengagement prediction (Linear Regression slopes per household)
- Basket analysis for cross-sell opportunities (association rules · Lift + Confidence)
- Demographic engagement (income, size, age, household composition)
- Seasonal trends (average weekly spend per month)
- Brand / organic share momentum over time

## Live Surface

| Page              | Purpose                                                                 |
|-------------------|-------------------------------------------------------------------------|
| `index.html`      | Login (username / email / password) against Azure SQL `Users`          |
| `register.html`   | Create an analyst account (PBKDF2-hashed password)                     |
| `dashboard.html`  | Executive dashboard · 6 KPIs + 4 charts + churn & basket tables · filterable by region / income / HH size / children |
| `search.html`     | Household data pull · sorted by basket, date, product, department, commodity (Req 4) |
| `upload.html`     | Drop in new Transactions / Households / Products CSVs, reloads tables atomically (Req 5) |

## Architecture

```
[ GitHub ] ──CI/CD──▶ [ Azure Static Web App ]  ──/api/*──▶ [ Azure Functions (Python) ] ──pymssql──▶ [ Azure SQL Database ]
     ▲                        │                                     │
     │                        ▼                                     ▼
   PRs/pushes           /src static content               shared_code/db.py, auth.py
```

### 1. Presentation tier — `/src`
Vanilla HTML5 + CSS3 (glassmorphism dark mode) + Chart.js. Zero build step.
Key scripts:
- `js/api.js` — transparent switch between the SWA `/api` proxy (prod) and the direct Functions host (file:// preview). Uniform `BrandShiftAPI.get/post/request` helpers.
- `js/session.js` — localStorage session guard.
- `js/app.js` — all page controllers (login / register / search / upload / dashboard).

Deployed by the workflow in `.github/workflows/azure-static-web-apps-*.yml`.

### 2. Logic tier — `/api` (Azure Functions, Python 3.11)

| Route                         | Method | Purpose                                                          |
|-------------------------------|--------|------------------------------------------------------------------|
| `/api/auth/register`          | POST   | Create a user · PBKDF2-SHA256 hashed                              |
| `/api/auth/login`             | POST   | Verify credentials · returns user profile                         |
| `/api/GetHousehold10`         | GET    | Strict demo pull for HH #10 (Req 3)                               |
| `/api/SearchData?hshd_num=N`  | GET    | Household demographics + transactions (Req 4)                     |
| `/api/UploadData`             | POST   | Multipart CSV ingestion into Transactions/Households/Products (Req 5) |
| `/api/analytics/kpis`         | GET    | Dashboard KPI tiles · supports filters (Req 6)                    |
| `/api/analytics/spend-trends` | GET    | National vs Private vs Organic quarterly time series              |
| `/api/analytics/churn`        | GET    | Per-household linear-regression slope + top-20 at-risk list (Req 8) |
| `/api/analytics/basket`       | GET    | Top commodity pair co-occurrence with Lift + Confidence (Req 7)   |
| `/api/analytics/demographics` | GET    | Avg spend per household bucketed by income / size / composition / age / children |
| `/api/analytics/seasonal`     | GET    | Avg weekly spend per calendar month                               |

Shared helpers in `api/shared_code`:
- `db.py` — pymssql connection from `SqlConnectionString`, CORS headers, JSON helpers, column cleaner.
- `auth.py` — PBKDF2 password hashing + verification, idempotent `Users` table bootstrap.

### 3. Data tier — Azure SQL Database

## Local Development

### Backend
```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp local.settings.json.example local.settings.json  # fill in SqlConnectionString
func start
```

### Frontend
Open `src/index.html` directly in a browser (file:// preview hits the live Functions host thanks to `js/api.js`) or run any static server rooted at `src/`.

## Requirement Mapping

| Req # | Deliverable                                   | Where it lives                                        |
|-------|-----------------------------------------------|-------------------------------------------------------|
| 1     | ML model write-up + CLV choice                | [`ML_Project_Submission.md`](ML_Project_Submission.md) |
| 2     | Login page (Username / Password / Email)       | `src/index.html` · backed by `/api/auth/login`        |
| 3     | Datastore + HH #10 pull                       | `api/schema.sql` + `api/GetHousehold10`               |
| 4     | Interactive search sorted Hshd→Commodity       | `src/search.html` · `api/SearchData`                  |
| 5     | Data loading web app                          | `src/upload.html` · `api/UploadData`                  |
| 6     | Dashboard of retail questions                 | `src/dashboard.html` · `api/AnalyticsKpis`, `Spend-Trends`, `Demographics`, `Seasonal` |
| 7     | Basket analysis (Random Forest discussion + live lift) | `ML_Project_Submission.md` + `api/AnalyticsBasket`   |
| 8     | Churn prediction                              | `api/AnalyticsChurn` + the churn chart / re-engagement table on `dashboard.html` |

## Azure Configuration Checklist

1. **Azure SQL firewall** must allow the Function App outbound IP.
2. **Application Settings** on the Function App:
   - `SqlConnectionString = Driver={ODBC Driver 18 for SQL Server};Server=tcp:<server>.database.windows.net,1433;Database=<db>;Uid=<user>;Pwd=<pwd>;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;`
   - `FUNCTIONS_WORKER_RUNTIME = python`
3. **CORS** on the Function App: add the Static Web App origin (or `*` for the course submission).
4. **Static Web App** is linked to this repo's `main` branch; the workflow in `.github/workflows` handles deployment of both `/src` and `/api`.

## Notes

- The `UploadData` endpoint disables foreign keys, truncates, bulk-inserts, then re-enables constraints so a household reload doesn't fail on orphaned transactions mid-load.
- The churn endpoint runs a pure-Python least-squares slope per household (no pandas/sklearn in the Function runtime) to keep the cold-start footprint small.
- Basket analysis runs entirely in Azure SQL via a CTE + self-join; only the top-N pairs come back to Python for Lift/Confidence arithmetic.
