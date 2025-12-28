# Project Management System (Blue Topbar Theme — v5)

This package contains **all files** for the complete Flask project.

### Highlights
- Global title **Project Management System** at the **very top** (above the blue top bar) on all pages; **centered, bold, larger**.
- **Login page** hides nav labels (Home/Time Entries) — only the **Login** button appears on the right.
- **After login**: blue topbar shows nav labels (**Home**, **Employees**, **Projects**, **Time Entries**), while the big title stays at the top.
- Clean classic CSS theme with cards, tables, shadows, and two Chart.js dashboards.

### Run
```bash
python -m venv .venv
# Windows
. .venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000/

### Demo accounts
- Admin: `admin` / `admin123`
- Employee: `Ismail` / `Ismail123`

### Seed sample data (optional)
```bash
python seeds.py
python app.py
```
