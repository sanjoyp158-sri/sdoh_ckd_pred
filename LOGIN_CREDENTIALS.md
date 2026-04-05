# Login Credentials

The backend uses real JWT authentication (not mock). Use these credentials to log in:

## Valid Credentials

### Provider Account
- **Username**: `provider1`
- **Password**: `password123`
- **Role**: Provider (can view patients, acknowledge alerts)

### Admin Account
- **Username**: `admin1`
- **Password**: `admin123`
- **Role**: Admin (full access)

## What Changed

The frontend now calls the real backend `/api/v1/auth/login` endpoint instead of using mock authentication. This means:

1. You must use valid credentials from the backend
2. You get a real JWT token
3. The token is validated on every API call
4. Invalid credentials will show an error message

## Testing Login

1. Start both backend and frontend servers
2. Open http://localhost:3000
3. Enter `provider1` / `password123`
4. Click "Sign In"
5. You should be redirected to the patient list

## Troubleshooting

**401 Unauthorized Error:**
- Make sure you're using the correct credentials above
- Check that the backend is running on port 8000
- Clear browser localStorage and try again

**"Error loading patients" after login:**
- The backend might not be running
- Check backend terminal for errors
- Verify: `curl http://localhost:8000/health`

## Adding More Users

To add more users, edit `backend/app/core/security.py` and add entries to the `MOCK_USERS` dictionary. Passwords are SHA256 hashed.

Generate a password hash:
```python
import hashlib
password = "your_password"
hashed = hashlib.sha256(password.encode()).hexdigest()
print(hashed)
```
