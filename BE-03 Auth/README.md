# BE-03 Auth — Login & Protect

A FastAPI authentication API using Supabase Auth. This project implements user signup, login, JWT verification, protected routes, and logout.

## Features

- User signup and login
- Access and refresh token responses
- Public and protected endpoints
- JWT verification using Supabase Auth
- Reusable authentication dependency
- Protected dashboard and profile routes
- Logout using the authenticated access token
- Interactive API documentation with Swagger UI

## Requirements

- Python 3.10 or newer
- A Supabase project
- pip

## Setup

1. Clone the repository and navigate to the `BE-03 Auth` directory.
2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Create a `.env` file by copying `.env.example`:

   ```bash
   cp .env.example .env
   ```

5. Add your Supabase project URL and anon/publishable key to `.env`.

   ```env
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your-supabase-anon-or-publishable-key
   PORT=8000
   ```

   Never commit your real `.env` file or expose your Supabase secrets.

## Run the API

```bash
uvicorn main:app --reload --port 8000
```

Open the interactive documentation at:

`http://127.0.0.1:8000/docs`

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/signup` | Register a user |
| POST | `/auth/login` | Authenticate and return tokens |
| POST | `/auth/logout` | Log out the authenticated session |
| GET | `/public/info` | Public information |
| GET | `/protected/profile` | Retrieve authenticated user profile |
| GET | `/protected/dashboard` | Access the protected dashboard |

Protected endpoints require a valid Supabase access token in the `Authorization: Bearer <token>` header.

## Environment Variables

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/publishable key |
| `PORT` | Local API port |

## Security

- Keep `.env` out of version control.
- Use a Supabase anon/publishable key, not the service-role key.
- Protected endpoints validate access tokens with Supabase Auth.
- Do not publish passwords, access tokens, refresh tokens, or private credentials.

## Testing

Use Swagger UI at `/docs` to test signup, login, public access, protected access, and logout. Authenticate through the Swagger **Authorize** control before testing protected routes.
