# Pedi Loan System

A Django-based loan management application for pedi loan collections and member loan tracking. The system includes admin and member dashboards, loan application workflows, payment tracking, Razorpay payment integration, and PDF/Excel export support.

## Key Features

- Admin and member authentication
- Admin dashboard with collections, active loans, and pending dues
- Member dashboard for personal loan and payment history
- Member management with search and CRUD operations
- Pedi management with assignment of members to pedi plans
- Loan management with interest calculation, repayment tracking, and status updates
- Loan application workflow with approval/rejection and configurable loan settings
- Monthly and one-time payment tracking
- Razorpay online payment integration
- Password reset and password change functionality
- JWT token-based API authentication endpoints
- Export members, payments, and loans to Excel

## Tech Stack

- Python 3
- Django 4.2.x
- Django REST framework
- SQLite
- Razorpay (payment gateway)

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd pedi_loan_system
```

### 2. Create and activate a virtual environment

On Windows (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root with values for:

```dotenv
SECRET_KEY=your-secret-key
DEBUG=True
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
```

### 5. Apply database migrations

```bash
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Run the development server

```bash
python manage.py runserver
```

Then open `http://127.0.0.1:8000/` in your browser.

## Application URLs

- Login: `/login/`
- Logout: `/logout/`
- Dashboard: `/dashboard/`
- Admin dashboard: `/admin-dashboard/`
- Member dashboard: `/member-dashboard/`
- Password reset: `/password-reset/`
- Password change: `/password-change/`
- Django admin: `/admin/`

## API Endpoints

- Obtain JWT tokens: `/api/token/`
- Refresh token: `/api/token/refresh/`

## Notes

- Static files are served from the `statics/` directory during development.
- Email sending uses the Django console backend by default.
- Razorpay payment configuration is required for online payment paths to work.

## License

This project is available for local development and customization.
