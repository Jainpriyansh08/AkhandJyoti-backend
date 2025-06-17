# Booking System Backend

A Django REST Framework based booking system with PostgreSQL database.

## Features

- Calendar-based slot booking system
- Online and assisted booking support
- WhatsApp and SMS notifications
- Email confirmations
- Admin panel for managing bookings, holidays, and settings
- Discount system with coupons
- Export functionality for booking data

## Prerequisites

- Docker and Docker Compose
- Python 3.11+
- PostgreSQL 15+
- Redis 7+

## Setup Instructions

1. Clone the repository:
```bash
git clone <repository-url>
cd booking-system
```

2. Create a `.env` file:
```bash
cp .env.example .env
```
Edit the `.env` file with your configuration.

3. Build and start the containers:
```bash
docker-compose up --build
```

4. Run migrations:
```bash
docker-compose exec web python manage.py migrate
```

5. Create a superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

6. Access the application:
- API: http://localhost:8000/api/
- Admin Panel: http://localhost:8000/admin/
- API Documentation: http://localhost:8000/api/docs/

## Project Structure

```
booking_system/
├── apps/
│   ├── bookings/
│   ├── core/
│   └── notifications/
├── config/
├── static/
└── templates/
```

## API Endpoints

- `/api/slots/` - List available slots
- `/api/bookings/` - Create and manage bookings
- `/api/holidays/` - Manage holidays
- `/api/discounts/` - Manage discount coupons
- `/api/staff/` - Manage staff codes

## Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run tests:
```bash
python manage.py test
```

3. Run linting:
```bash
flake8
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License. 