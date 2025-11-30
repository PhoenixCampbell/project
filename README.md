# 📘 Faculty–Class Match System

_A full-stack DSU scheduling support system for collecting faculty preferences, running a solver, and generating optimized teaching assignments._

## 🧭 Project Overview

Faculty–Class Match is a web application built for the Dakota State University Software Engineering course (CSC 470). The system allows:

-   **Faculty** to submit course preferences including comfort level & wanting to teach level
-   **Administration** to run an automated solver using Python
-   **The system** to export a solution Excel file for review

The project is implemented as a **full-stack application** using:

-   **HTML/CSS/Bootstrap** – UI & layout
-   **Vanilla JavaScript** – dynamic behavior
-   **Express.js (Node)** – backend + API routes
-   **Python (solver.py)** – optimization engine
-   **CSV file storage** – faculty preference persistence

---

# 🚀 Current Progress (Backlog Summary)

## ✅ Sprint 1 — Core MVP (Completed)

| ID      | Story                            | Status         | Assignee |
| ------- | -------------------------------- | -------------- | -------- |
| **1.1** | New faculty input page           | 🟡 In Progress | Ryan     |
| **1.2** | Dynamic JSON-based class loading | ✅ Completed   | Phoenix  |
| **1.3** | Lock/unlock UI workflow          | ✅ Completed   | Phoenix  |
| **1.4** | Comfort & Desire rating system   | ✅ Completed   | Phoenix  |
| **1.5** | Save & Submit (CSV output)       | ✅ Completed   | Phoenix  |

### ✔ Delivered in Sprint 1

-   Full faculty input workflow
-   Term → Class dynamic lookup
-   Rating system (comfort & desire)
-   CSV storage with auto-append
-   Faculty ID auto-detection
-   Fully validated submit workflow
-   Express server setup

---

## 🧩 Sprint 2 — Solver Integration (In Progress)

| ID      | Story                          | Status         | Assignee |
| ------- | ------------------------------ | -------------- | -------- |
| **2.1** | Trigger solver from admin page | ✅ Completed   | Phoenix  |
| **2.2** | Connect solver.py              | 🟡 In Progress | Ryan     |
| **2.3** | Generate Excel output          | 🚧 Coming Soon | Zack     |
| **3.1** | Downloadable Prof Preferences  | 🚧 Coming Soon | Andy     |
| **4.2** | Linting Validation             | ✅ Completed   | Andy     |

### ✔ Completed so far

-   Admin UI created (`admin.html`)
-   Run Solver button
-   `/api/admin/solve` backend route
-   Python execution via `child_process.spawn()`
-   Graceful handling for missing solver.py
-   Placeholder for `solution.xlsx`

---

# 🏗️ System Architecture

```
faculty.html ─────────────┐
admin.html   ─────────────┤──→ Express Backend (server.js)
                          │
                          └──→ CSV Storage (/data)
                                   │
                                   ▼
                               solver.py (Python)
                                   │
                                   ▼
                              solution.xlsx
```

---

# 📄 API Documentation

## POST /api/preferences/submit

Submit a single faculty preference.

### Request:

```json
{
	"facultyId": "john.doe",
	"termCode": "202580",
	"termLabel": "Fall 2025",
	"classId": "CSC210-D01",
	"classLabel": "Principles of Accounting I",
	"rating": 4,
	"desireRating": 3
}
```

## POST /api/admin/solve

Runs the Python solver.

### Example Success Response:

```json
{
	"success": true,
	"message": "Solver completed and solution.xlsx was generated."
}
```

### Missing solver.py:

```json
{
	"success": false,
	"message": "Solver script not found"
}
```

---

# 🛠️ Local Development

## Install dependencies

```bash
npm install
```

## Run server

```bash
node server.js
```

## Access pages

```
http://localhost:3000/index.html
http://localhost:3000/faculty.html
http://localhost:3000/admin.html
```

---

# 📁 Project Structure

```
/data
   prefs_<faculty>_<term>.csv
   solution.xlsx

/server.js
/solver.py
/faculty.html
/admin.html
/css/styles.css
```

---

# 🚧 Upcoming (Sprint 3 & 4)

### Sprint 3 — Admin Tools

-   Export aggregated faculty preferences
-   Conflict detection
-   Searchable/class-filter view

### Sprint 4 — Deployment

-   Hosting on bim.inclass.today
-   SSL + production express config
-   Production logs
-   Final UI polish

---

# 🤝 Contributing

1. Branch using:
    ```
    feature/<story-id>-<description>
    ```
2. Run ESLint
3. Submit PR to `main`

---

# 🎉 Team

| Member      | Role                    | Work                            |
| ----------- | ----------------------- | ------------------------------- |
| Phoenix     | Frontend + Backend Lead | Sprint 1 + major Sprint 2 items |
| Zack        | Solver + Export         | Sprint 2 work                   |
| Ryan        | Review + Documentation  | UI/UX + Python integration      |
| Andy        | Review + Documentation  | Cleanup + p2p integration       |
| Alex        | Review + Documentation  | Backlog, README, PR reviews     |
| All Members | Review + Documentation  | Backlog, README, PR reviews     |
