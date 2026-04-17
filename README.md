# BrandShift Cloud Data Analytics
**University of Cincinnati Cloud Computing Final Project 2026**

## 🎯 Project Goal
The goal of this project is to build an end-to-end, full-stack predictive data analytics solution utilizing Azure Cloud Technologies. By analyzing the 84.51° Retail Sample Dataset (Households, Transactions, and Products), this project securely pulls, displays, and visualizes retail challenges (like Brand Preference, Churn, and Basket Analysis) to drive high-impact strategic insights for Customer Lifetime Value management.

---

## 🏗️ Cloud Infrastructure & Architecture Layer

This application is decoupled into three primary, highly-scalable cloud tiers:

### 1. The Presentation Tier (Frontend Web UI)
- **Tech Stack:** Vanilla HTML5, CSS3 (Glassmorphism Dark Mode), JavaScript (ES6+), and Chart.js.
- **Location in Repo:** `/src` folder.
- **Azure Hosting:** Hosted via **Azure Static Web Apps**. 
- **Connectivity:** Pulled continuously from this GitHub repository via embedded CI/CD GitHub Actions. The frontend makes asynchronous `fetch()` API calls to the remote Azure Serverless Functions and natively visualizes the matrices and dashboards in real-time.

### 2. The Logic Tier (Serverless Backend API)
- **Tech Stack:** Python 3.11+, `pymssql`, `pandas`, Azure Functions v1 Programming Model.
- **Location in Repo:** `/api` folder.
- **Azure Hosting:** Hosted via **Azure Functions (Linux Serverless Consumption Plan)**.
- **Connectivity:** 
  - Resolves CORS via Azure Portal allowing the frontend to pull data seamlessly. 
  - Exposes 3 distinct REST endpoints:
    - `GET /api/GetHousehold10`: Strictly formatted explicit demonstration pull.
    - `GET /api/SearchData`: Dynamic parameterized GET endpoint for any household cross-reference.
    - `POST /api/UploadData`: Multi-part CSV file ingestion endpoint feeding straight natively to the Azure SQL Cloud.

### 3. The Data Tier (Cloud Database)
- **Tech Stack:** Microsoft Azure SQL Database.
- **Location in Repo:** Provisioned off-repo, schemas tracked in `api/schema.sql`.
- **Azure Hosting:** **Azure SQL Server / Azure SQL Database**.
- **Connectivity:** Integrates directly with the Python Serverless environment through heavily resilient connection strings securely stored as Application Setting Environment Variables, accessed exclusively by the `pymssql` engine to perfectly bypass missing Cloud Container OS drivers.

---

## 🤖 Analytics & Predictive Machine Learning Models
While building actionable dashboards allows visual trend-spotting, complex decisions like **Customer Lifetime Value**, **Cross-Selling**, and **Disengagement Trends** are tracked using rigorous ML methodologies. 

The explicit syntax and business-logic strategy for these models (utilizing `RandomForestClassifier` for Cross-Basket probability mapping and `LinearRegression` for mathematical churn slopes!) are fully provided internally in the **`ML_Project_Submission.md`** file submitted alongside this cloud repository codebase.
