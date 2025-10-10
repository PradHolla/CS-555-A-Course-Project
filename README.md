# 🚀 Student Starter Pack - SSW555 Project Template

A collection of beautifully designed, production-ready web applications built with Flask, SQLAlchemy, and Tailwind CSS. Perfect for students looking to jumpstart their SSW555 course projects.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-3.0-38B2AC.svg)
![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)
![CI](https://github.com/SIT-RiSE/SSW555-Example-Project/workflows/CI/badge.svg)
![Tests](https://github.com/SIT-RiSE/SSW555-Example-Project/workflows/Quick%20Test/badge.svg)

## ✨ What's Inside

Four complete, production-ready applications to choose from:

- **🌱 Habit Tracker** - Daily habit tracking with streak counters and progress visualization
- **☁️ Mood Journal** - Emotional wellness tracking with mood scales and reflection notes
- **💳 Expense Splitter** - Smart expense splitting with multi-participant support
- **🍳 Recipe Assistant** - Recipe storage with ingredients, instructions, and prep time tracking

Each app features modern UI design, form handling, and database persistence. Pick one, customize it, and build your project on top of it!

**➡️ New to the starter pack? Start here: [Quick Start Guide](docs/QUICK_START.md)**

## ⚡ Installation

### Prerequisites

- Python 3.9+
- [uv](https://github.com/astral-sh/uv) (Python package manager)

### Installation

```bash
# Clone and navigate
git clone https://github.com/yourusername/SSW555-Example-Project.git
cd SSW555-Example-Project

# Install dependencies
uv sync

# Run the application (uv automatically handles the virtual environment)
uv run python app.py

# Open browser at http://localhost:5000

# Run tests (optional)
uv run pytest -v
```

## 📁 Project Structure

```
SSW555-Example-Project/
├── app.py              # Main Flask application with routes
├── models.py           # Database models (Habit, MoodEntry, Expense, Recipe)
├── extensions.py       # Shared SQLAlchemy instance
├── pyproject.toml      # Project dependencies (managed by uv)
├── uv.lock             # Dependency lock file
│
├── docs/               # Documentation
│   ├── CI.md
│   ├── CUSTOMIZATION.md
│   ├── DATABASE.md
│   ├── DEVELOPMENT.md
│   ├── QUICK_START.md
│   ├── SEPARATION.md
│   ├── TESTING.md
│   └── TROUBLESHOOTING.md
│
├── .github/            # GitHub configuration
│   └── workflows/
│       ├── ci.yml           # Main CI/CD pipeline
│       └── quick-test.yml   # Fast test workflow
│
├── tests/              # Unit and integration tests
│   ├── __init__.py
│   ├── conftest.py      # Pytest fixtures
│   ├── test_models.py   # Model unit tests
│   └── test_routes.py   # Route integration tests
│
├── templates/          # Jinja2 templates
│   ├── base.html       # Shared layout & navigation
│   ├── home/           # Landing page
│   └── apps/           # Individual app templates
│       ├── habit_tracker/
│       ├── mood_journal/
│       ├── expense_splitter/
│       └── recipe_assistant/
│
├── static/             # Static files
│   └── css/
│       └── style.css   # Global styles
│
└── instance/           # Instance-specific files (auto-created)
    └── app.db          # SQLite database
```

## 🎨 Customization

### Choosing Your Module

1. Explore all modules at `http://localhost:5000`
2. Pick the one that fits your project
3. Remove unwanted routes from `app.py`
4. Delete unused template folders from `templates/apps/`

**📖 Detailed guide:** [docs/CUSTOMIZATION.md](docs/CUSTOMIZATION.md)

### Next Steps

- **Extend models** - Add new fields or relationships
- **Create new routes** - Build additional features
- **Customize styling** - Modify Tailwind classes or add custom CSS
- **Add authentication** - Use Flask-Login for user management

## 📚 Documentation
-----
- **[Quick Start Guide](docs/QUICK_START.md)** ⭐ - Pick a module and clean up the rest (start here!)
- **[CI Quick Start](CI_QUICKSTART.md)** 🚦 - Understand what the GitHub Actions workflows do and how to mirror them locally
-----
- **[Testing Guide](docs/TESTING.md)** - Writing and running tests, test organization, best practices
- **[CI/CD Guide](docs/CI.md)** - Deep dive into GitHub Actions configuration and customization
- **[Customization Guide](docs/CUSTOMIZATION.md)** - Extend models, add routes, and restyle the modules you keep
- **[Database Management](docs/DATABASE.md)** - Schema operations, migrations, and query examples
- **[Development Guide](docs/DEVELOPMENT.md)** - Environment setup, architecture, debugging, deployment
- **[Frontend-Backend Separation](docs/SEPARATION.md)** 🔄 - Convert this project to REST API + modern frontend framework
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

## 🛠️ Tech Stack

- **Backend:** Flask 3.0+ with SQLAlchemy
- **Database:** SQLite (easy to switch to PostgreSQL)
- **Frontend:** Tailwind CSS (via CDN)
- **Template Engine:** Jinja2
- **Architecture:** Monolithic with Server-Side Rendering (SSR)

### 📐 Architecture Note

This project uses a **traditional monolithic architecture** with server-side rendering:
- Backend and frontend are coupled together
- Flask renders HTML templates using Jinja2
- Pages reload on navigation (traditional web app)

**Not a frontend-backend separated architecture** (no REST API, no React/Vue/Angular)

**Want to convert to a separated architecture?** See our guide: **[Frontend-Backend Separation](docs/SEPARATION.md)** 🔄

## 🎓 Course Information

**Course:** SSW555 - Agile Methods for Software Development
**Institution:** Stevens Institute of Technology
**Purpose:** Educational template for rapid prototyping

## 🤝 Contributing

This is a student project template. Feel free to:
- Fork and customize for your needs
- Submit issues for bugs
- Share improvements with classmates

## 📝 License

MIT License - Open source and free to use

---

**Happy Coding!** 🎉

*Built with ❤️ for SSW555 students*
