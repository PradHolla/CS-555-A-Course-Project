# Frontend-Backend Separation Guide

This guide walks you through converting the monolithic SSW555 starter project into a **separated frontend-backend architecture** with a REST API backend and a modern JavaScript frontend.

## Table of Contents
- [Overview](#overview)
- [Current Architecture](#current-architecture)
- [Target Architecture](#target-architecture)
- [Step 1: Create REST API Backend](#step-1-create-rest-api-backend)
- [Step 2: Add CORS Support](#step-2-add-cors-support)
- [Step 3: Create React Frontend](#step-3-create-react-frontend)
- [Step 4: Test the Separated Architecture](#step-4-test-the-separated-architecture)
- [Alternative Frontend Frameworks](#alternative-frontend-frameworks)
- [Deployment Considerations](#deployment-considerations)

## Overview

### Why Separate Frontend and Backend?

**Advantages:**
- ✅ Independent development and deployment
- ✅ Better scalability
- ✅ API can be reused by mobile apps, third-party clients
- ✅ Modern UI frameworks (React, Vue, Angular)
- ✅ Better separation of concerns

**Disadvantages:**
- ❌ More complex setup and deployment
- ❌ CORS configuration needed
- ❌ Two codebases to maintain
- ❌ SEO challenges (if not using SSR)
- ❌ Slower initial page load

### When to Choose Separation?

**Use separated architecture if:**
- Building a Single Page Application (SPA)
- Need mobile app support
- Want to use React/Vue/Angular
- Team has separate frontend/backend developers
- Need independent scaling

**Keep monolithic if:**
- Building a simple CRUD app
- SEO is critical
- Small team or solo developer
- Need faster development time

## Current Architecture

```
Client Browser
      ↓
Flask App (app.py)
      ↓
Templates (Jinja2) → Rendered HTML
      ↓
SQLAlchemy → SQLite
```

**Data flow:**
1. Browser sends request to Flask
2. Flask processes request
3. Flask renders Jinja2 template with data
4. HTML sent back to browser
5. Page reloads on navigation

## Target Architecture

```
Client Browser (React App)
      ↓ HTTP/AJAX
Flask REST API (app.py)
      ↓ JSON
SQLAlchemy → SQLite
```

**Data flow:**
1. React app sends AJAX request
2. Flask API returns JSON
3. React updates UI dynamically
4. No page reload (SPA)

---

## Step 1: Create REST API Backend

### 1.1 Install Flask-CORS

Add CORS support to allow frontend to access backend API:

```bash
uv pip install flask-cors
```

### 1.2 Create API Routes

Create a new file `api.py` for REST API endpoints:

```python
# api.py
from flask import Blueprint, jsonify, request
from extensions import db
from models import Habit, MoodEntry, Expense, Recipe

api = Blueprint('api', __name__, url_prefix='/api')

# ===== Habit API =====

@api.route('/habits', methods=['GET'])
def get_habits():
    """Get all habits"""
    habits = Habit.query.order_by(Habit.created_at.desc()).all()
    return jsonify([{
        'id': h.id,
        'name': h.name,
        'description': h.description,
        'created_at': h.created_at.isoformat(),
        'completed_dates': h.completed_dates
    } for h in habits])


@api.route('/habits', methods=['POST'])
def create_habit():
    """Create a new habit"""
    data = request.get_json()

    if not data or not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400

    habit = Habit(
        name=data['name'].strip(),
        description=data.get('description', '').strip() or None
    )
    db.session.add(habit)
    db.session.commit()

    return jsonify({
        'id': habit.id,
        'name': habit.name,
        'description': habit.description,
        'created_at': habit.created_at.isoformat()
    }), 201


@api.route('/habits/<int:habit_id>', methods=['GET'])
def get_habit(habit_id):
    """Get a specific habit"""
    habit = Habit.query.get_or_404(habit_id)
    return jsonify({
        'id': habit.id,
        'name': habit.name,
        'description': habit.description,
        'created_at': habit.created_at.isoformat(),
        'completed_dates': habit.completed_dates
    })


@api.route('/habits/<int:habit_id>', methods=['PUT'])
def update_habit(habit_id):
    """Update a habit"""
    habit = Habit.query.get_or_404(habit_id)
    data = request.get_json()

    if data.get('name'):
        habit.name = data['name'].strip()
    if 'description' in data:
        habit.description = data['description'].strip() or None
    if 'completed_dates' in data:
        habit.completed_dates = data['completed_dates']

    db.session.commit()

    return jsonify({
        'id': habit.id,
        'name': habit.name,
        'description': habit.description,
        'created_at': habit.created_at.isoformat(),
        'completed_dates': habit.completed_dates
    })


@api.route('/habits/<int:habit_id>', methods=['DELETE'])
def delete_habit(habit_id):
    """Delete a habit"""
    habit = Habit.query.get_or_404(habit_id)
    db.session.delete(habit)
    db.session.commit()
    return '', 204


# ===== Mood Entry API =====

@api.route('/moods', methods=['GET'])
def get_moods():
    """Get all mood entries"""
    entries = MoodEntry.query.order_by(MoodEntry.created_at.desc()).all()
    return jsonify([{
        'id': e.id,
        'mood': e.mood,
        'notes': e.notes,
        'created_at': e.created_at.isoformat()
    } for e in entries])


@api.route('/moods', methods=['POST'])
def create_mood():
    """Create a new mood entry"""
    data = request.get_json()

    if not data or not data.get('mood'):
        return jsonify({'error': 'Mood is required'}), 400

    entry = MoodEntry(
        mood=data['mood'].strip(),
        notes=data.get('notes', '').strip() or None
    )
    db.session.add(entry)
    db.session.commit()

    return jsonify({
        'id': entry.id,
        'mood': entry.mood,
        'notes': entry.notes,
        'created_at': entry.created_at.isoformat()
    }), 201


# ===== Expense API =====

@api.route('/expenses', methods=['GET'])
def get_expenses():
    """Get all expenses"""
    expenses = Expense.query.order_by(Expense.created_at.desc()).all()
    return jsonify([{
        'id': e.id,
        'description': e.description,
        'amount': e.amount,
        'payer': e.payer,
        'participants': e.participants,
        'created_at': e.created_at.isoformat()
    } for e in expenses])


@api.route('/expenses', methods=['POST'])
def create_expense():
    """Create a new expense"""
    data = request.get_json()

    if not data or not data.get('description') or not data.get('amount') or not data.get('payer'):
        return jsonify({'error': 'Description, amount, and payer are required'}), 400

    try:
        amount = float(data['amount'])
    except ValueError:
        return jsonify({'error': 'Invalid amount'}), 400

    expense = Expense(
        description=data['description'].strip(),
        amount=amount,
        payer=data['payer'].strip(),
        participants=data.get('participants', '').strip() or None
    )
    db.session.add(expense)
    db.session.commit()

    return jsonify({
        'id': expense.id,
        'description': expense.description,
        'amount': expense.amount,
        'payer': expense.payer,
        'participants': expense.participants,
        'created_at': expense.created_at.isoformat()
    }), 201


# ===== Recipe API =====

@api.route('/recipes', methods=['GET'])
def get_recipes():
    """Get all recipes"""
    recipes = Recipe.query.order_by(Recipe.created_at.desc()).all()
    return jsonify([{
        'id': r.id,
        'name': r.name,
        'ingredients': r.ingredients,
        'instructions': r.instructions,
        'prep_time': r.prep_time,
        'created_at': r.created_at.isoformat()
    } for r in recipes])


@api.route('/recipes', methods=['POST'])
def create_recipe():
    """Create a new recipe"""
    data = request.get_json()

    if not data or not data.get('name') or not data.get('ingredients') or not data.get('instructions'):
        return jsonify({'error': 'Name, ingredients, and instructions are required'}), 400

    prep_time = None
    if data.get('prep_time'):
        try:
            prep_time = int(data['prep_time'])
            if prep_time < 0:
                prep_time = None
        except ValueError:
            prep_time = None

    recipe = Recipe(
        name=data['name'].strip(),
        ingredients=data['ingredients'].strip(),
        instructions=data['instructions'].strip(),
        prep_time=prep_time
    )
    db.session.add(recipe)
    db.session.commit()

    return jsonify({
        'id': recipe.id,
        'name': recipe.name,
        'ingredients': recipe.ingredients,
        'instructions': recipe.instructions,
        'prep_time': recipe.prep_time,
        'created_at': recipe.created_at.isoformat()
    }), 201
```

### 1.3 Update app.py

Modify `app.py` to register the API blueprint:

```python
# Add this import at the top
from flask_cors import CORS

# After creating the Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# ... existing config ...

# Register API blueprint (add after db.init_app(app))
from api import api
app.register_blueprint(api)

# Keep existing template routes or remove them if going full SPA
```

### 1.4 Test the API

Start the Flask server:
```bash
uv run python app.py
```

Test with curl or Postman:
```bash
# Get all habits
curl http://localhost:5000/api/habits

# Create a habit
curl -X POST http://localhost:5000/api/habits \
  -H "Content-Type: application/json" \
  -d '{"name": "Exercise", "description": "30 min daily"}'

# Get a specific habit
curl http://localhost:5000/api/habits/1
```

---

## Step 2: Add CORS Support

CORS (Cross-Origin Resource Sharing) allows your frontend (running on a different port) to access the backend API.

### 2.1 Install Flask-CORS

Already done in Step 1.1, but if not:
```bash
uv pip install flask-cors
```

### 2.2 Configure CORS

In `app.py`:

```python
from flask_cors import CORS

app = Flask(__name__)

# Allow specific origins (for production)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://localhost:5173"],  # React/Vite dev servers
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type"]
    }
})

# Or allow all origins (for development only)
# CORS(app)
```

---

## Step 3: Create React Frontend

### 3.1 Create React App with Vite

In a new directory (outside the Flask project):

```bash
# Create React app
npm create vite@latest frontend -- --template react
cd frontend
npm install

# Install dependencies
npm install axios
```

### 3.2 Create Habit Tracker Component

Create `src/components/HabitTracker.jsx`:

```jsx
import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

function HabitTracker() {
  const [habits, setHabits] = useState([]);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);

  // Fetch habits on component mount
  useEffect(() => {
    fetchHabits();
  }, []);

  const fetchHabits = async () => {
    try {
      const response = await axios.get(`${API_BASE}/habits`);
      setHabits(response.data);
    } catch (error) {
      console.error('Error fetching habits:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await axios.post(`${API_BASE}/habits`, {
        name,
        description
      });

      setName('');
      setDescription('');
      fetchHabits(); // Refresh the list
    } catch (error) {
      console.error('Error creating habit:', error);
      alert('Failed to create habit');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure?')) return;

    try {
      await axios.delete(`${API_BASE}/habits/${id}`);
      fetchHabits(); // Refresh the list
    } catch (error) {
      console.error('Error deleting habit:', error);
      alert('Failed to delete habit');
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8">Habit Tracker</h1>

      {/* Create Form */}
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow mb-8">
        <div className="mb-4">
          <label className="block text-gray-700 font-semibold mb-2">
            Habit Name *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-4 py-2 border rounded-lg"
            required
          />
        </div>

        <div className="mb-4">
          <label className="block text-gray-700 font-semibold mb-2">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full px-4 py-2 border rounded-lg"
            rows="3"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? 'Adding...' : 'Add Habit'}
        </button>
      </form>

      {/* Habits List */}
      <div className="space-y-4">
        {habits.map((habit) => (
          <div key={habit.id} className="bg-white p-6 rounded-lg shadow">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-xl font-semibold">{habit.name}</h3>
                {habit.description && (
                  <p className="text-gray-600 mt-2">{habit.description}</p>
                )}
                <p className="text-sm text-gray-400 mt-2">
                  Created: {new Date(habit.created_at).toLocaleDateString()}
                </p>
              </div>
              <button
                onClick={() => handleDelete(habit.id)}
                className="text-red-600 hover:text-red-800"
              >
                Delete
              </button>
            </div>
          </div>
        ))}

        {habits.length === 0 && (
          <p className="text-center text-gray-500 py-8">
            No habits yet. Create your first one!
          </p>
        )}
      </div>
    </div>
  );
}

export default HabitTracker;
```

### 3.3 Update App.jsx

Replace `src/App.jsx`:

```jsx
import HabitTracker from './components/HabitTracker';
import './App.css';

function App() {
  return (
    <div className="min-h-screen bg-gray-100">
      <HabitTracker />
    </div>
  );
}

export default App;
```

### 3.4 Add Tailwind CSS (Optional)

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Update `tailwind.config.js`:
```js
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

Update `src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 3.5 Run the React App

```bash
npm run dev
```

Visit `http://localhost:5173` - you should see the Habit Tracker UI!

---

## Step 4: Test the Separated Architecture

### 4.1 Start Both Servers

**Terminal 1 - Backend:**
```bash
cd SSW555-Example-Project
uv run python app.py
# Running on http://localhost:5000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
# Running on http://localhost:5173
```

### 4.2 Test the Flow

1. Open `http://localhost:5173` in browser
2. Create a new habit
3. Verify it appears in the list
4. Delete a habit
5. Check browser DevTools Network tab - you should see AJAX requests to `http://localhost:5000/api/habits`

### 4.3 Verify API Directly

```bash
# In Terminal 3
curl http://localhost:5000/api/habits
```

You should see JSON response with the habits you created.

---

## Alternative Frontend Frameworks

### Vue.js

Create Vue app:
```bash
npm create vue@latest frontend
cd frontend
npm install axios
```

Habit component (`src/components/HabitTracker.vue`):
```vue
<template>
  <div class="habit-tracker">
    <h1>Habit Tracker</h1>

    <form @submit.prevent="createHabit">
      <input v-model="name" placeholder="Habit name" required />
      <textarea v-model="description" placeholder="Description"></textarea>
      <button type="submit">Add Habit</button>
    </form>

    <div v-for="habit in habits" :key="habit.id" class="habit-card">
      <h3>{{ habit.name }}</h3>
      <p>{{ habit.description }}</p>
      <button @click="deleteHabit(habit.id)">Delete</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';
const habits = ref([]);
const name = ref('');
const description = ref('');

const fetchHabits = async () => {
  const response = await axios.get(`${API_BASE}/habits`);
  habits.value = response.data;
};

const createHabit = async () => {
  await axios.post(`${API_BASE}/habits`, {
    name: name.value,
    description: description.value
  });
  name.value = '';
  description.value = '';
  fetchHabits();
};

const deleteHabit = async (id) => {
  await axios.delete(`${API_BASE}/habits/${id}`);
  fetchHabits();
};

onMounted(fetchHabits);
</script>
```

### Angular

Create Angular app:
```bash
npm install -g @angular/cli
ng new frontend
cd frontend
npm install axios
```

Service (`src/app/habit.service.ts`):
```typescript
import { Injectable } from '@angular/core';
import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

@Injectable({ providedIn: 'root' })
export class HabitService {
  async getHabits() {
    const response = await axios.get(`${API_BASE}/habits`);
    return response.data;
  }

  async createHabit(name: string, description: string) {
    const response = await axios.post(`${API_BASE}/habits`, { name, description });
    return response.data;
  }

  async deleteHabit(id: number) {
    await axios.delete(`${API_BASE}/habits/${id}`);
  }
}
```

---

## Deployment Considerations

### Development vs Production

**Development:**
- Frontend: `http://localhost:5173` (Vite dev server)
- Backend: `http://localhost:5000` (Flask dev server)
- CORS: Allow localhost origins

**Production:**
- Frontend: Served from CDN or web server (Nginx, Vercel, Netlify)
- Backend: Production WSGI server (Gunicorn, uWSGI)
- CORS: Restrict to production domain only

### Deployment Options

#### Option 1: Separate Deployments

**Backend (Flask API):**
```bash
# Deploy to Heroku, Railway, Render, etc.
# Configure production database (PostgreSQL)
```

**Frontend (React):**
```bash
# Build production bundle
npm run build

# Deploy to Vercel, Netlify, GitHub Pages
# Set API_BASE to production API URL
```

#### Option 2: Single Server Deployment

Build React and serve static files from Flask:

```bash
# Build React app
cd frontend
npm run build

# Copy build files to Flask static folder
cp -r dist/* ../static/

# Update Flask to serve React app
```

In `app.py`:
```python
from flask import send_from_directory

@app.route('/')
def serve_react():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)
```

### Environment Variables

**Frontend (.env):**
```
VITE_API_BASE=http://localhost:5000/api
```

In React:
```js
const API_BASE = import.meta.env.VITE_API_BASE;
```

**Backend:**
```python
import os

CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')
CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}})
```

---

## Testing the Separated Architecture

### Backend API Tests

Update `tests/test_routes.py` to test API endpoints:

```python
def test_api_get_habits_returns_json(client):
    """Test that GET /api/habits returns JSON"""
    response = client.get('/api/habits')
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    data = response.get_json()
    assert isinstance(data, list)


def test_api_create_habit_returns_json(client):
    """Test that POST /api/habits creates habit and returns JSON"""
    response = client.post(
        '/api/habits',
        json={'name': 'Exercise', 'description': 'Daily workout'}
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'Exercise'
    assert 'id' in data
```

### Frontend Tests

Using Vitest for React:

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom
```

`src/components/HabitTracker.test.jsx`:
```jsx
import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import HabitTracker from './HabitTracker';
import axios from 'axios';

vi.mock('axios');

test('renders habit tracker', () => {
  axios.get.mockResolvedValue({ data: [] });
  render(<HabitTracker />);
  expect(screen.getByText('Habit Tracker')).toBeInTheDocument();
});

test('displays habits from API', async () => {
  const mockHabits = [
    { id: 1, name: 'Exercise', description: 'Daily workout', created_at: '2025-01-01' }
  ];
  axios.get.mockResolvedValue({ data: mockHabits });

  render(<HabitTracker />);

  await waitFor(() => {
    expect(screen.getByText('Exercise')).toBeInTheDocument();
  });
});
```

---

## Summary

You've now converted the monolithic SSW555 starter project into a separated architecture:

✅ **Backend:** Flask REST API with JSON responses
✅ **Frontend:** React SPA with Axios for API calls
✅ **CORS:** Configured for cross-origin requests
✅ **Testing:** API tests for backend, component tests for frontend
✅ **Deployment:** Ready for separate or combined deployment

### Next Steps

1. **Add authentication:** JWT tokens, session management
2. **Add state management:** Redux, Zustand, or React Context
3. **Add routing:** React Router for multiple pages
4. **Add real-time features:** WebSockets with Flask-SocketIO
5. **Add file uploads:** Handle images, documents
6. **Add pagination:** For large datasets
7. **Add search/filtering:** Advanced query capabilities

### Resources

- [Flask REST API Tutorial](https://flask.palletsprojects.com/en/latest/tutorial/)
- [React Documentation](https://react.dev)
- [Axios Documentation](https://axios-http.com)
- [Flask-CORS Documentation](https://flask-cors.readthedocs.io/)
