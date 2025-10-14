# SprintPay - Expense Management

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?style=for-the-badge)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg?style=for-the-badge)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.0-38B2AC.svg?style=for-the-badge)
![CI/CD](https://github.com/PradHolla/CS-555-A-Course-Project/actions/workflows/ci.yml/badge.svg)

SprintPay is an intelligent expense management application designed to simplify shared finances for groups such as roommates, travelers, and student clubs. The platform moves beyond basic expense splitting by incorporating AI-driven features to provide a seamless and insightful user experience.

---

## Table of Contents
1. [Project Description](#project-description)
2. [Core Features](#core-features)
3. [The Team](#the-team)
4. [Tech Stack](#tech-stack)
5. [Getting Started](#getting-started)
6. [Project Board](#project-board)
7. [License](#license)

---

## Project Description

Our mission is to eliminate the complexity and stress of shared expenses by providing an intelligent, automated, and transparent financial tool for groups. SprintPay allows users to create groups, track shared expenses with advanced features like multi-currency support and receipt attachments, and settle up debts efficiently. Building on this foundation, the application integrates intelligent systems to offer personalized savings tips, spending reports, and alerts for unusual activity.

---

## Core Features

* **Group Management:** Create private groups, invite members via email, and manage roles.
* **Advanced Expense Tracking:** Add expenses with support for recurring bills, categorization, receipt attachments, and multi-currency conversion.
* **Transparent Balances:** View real-time dashboards of who owes whom, detailed activity feeds, and a "Simplify Debts" feature to calculate the most efficient payment paths.
* **Intelligent Notifications:** Receive payment reminders, settlement confirmations, and daily activity digests.
* **Modern User Experience:** Secure authentication with OTP, a user-friendly interface, and a dark mode option.

---

## The Team

* Sairithik Komuravelly
* Pranav Itikarlapalli
* Rishabh Ravi Madne
* Pradhyumna Nagaraja Holla
* Anikait Targolli

---

## Tech Stack

This project is built with a Python-based web stack, customized from the SSW555-Example-Project starter package.

* **Backend:** Flask, SQLAlchemy
* **Database:** SQLite
* **Frontend:** Jinja2 (Templating), Tailwind CSS
* **Package Management:** uv
* **Testing:** Pytest, pytest-cov
* **CI/CD:** GitHub Actions
* **Code Quality:** Ruff (Linting & Formatting), Bandit (Security)

---

## Getting Started

To get a local copy up and running, follow these simple steps.

### Prerequisites

* Python 3.9+
* [uv](https://github.com/astral-sh/uv) (Python package manager)

### Installation & Setup

1.  **Clone the repo**
    ```sh
    git clone [your-repo-link]
    cd CS-555-A-Course-Project
    ```

2.  **Install dependencies**
    ```sh
    uv sync
    ```

3.  **Run the application**
    * `uv` automatically handles the virtual environment.
    ```sh
    uv run python app.py
    ```

4.  **View the app**
    * Open your browser and navigate to `http://localhost:5000`

5.  **Run tests (optional)**
    ```sh
    uv run pytest -v
    ```

---

## Project Board

All our user stories, tasks, and sprint progress are tracked on our GitHub Projects board.

* **[Link to SprintPay Project Board]** *(https://github.com/users/PradHolla/projects/1/views/1)*

---

## License

Distributed under the MIT License. See `LICENSE` for more information.