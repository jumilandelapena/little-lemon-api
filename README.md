# Little Lemon Restaurant API

![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![Django 6.1](https://img.shields.io/badge/django-6.1-092E20?logo=django&logoColor=white)
![DRF 3.18](https://img.shields.io/badge/DRF-3.18-A30000)
![License MIT](https://img.shields.io/badge/license-MIT-green)
[![CI](https://github.com/jumilandelapena/little-lemon-api/actions/workflows/ci.yml/badge.svg)](https://github.com/jumilandelapena/little-lemon-api/actions/workflows/ci.yml)

A REST API for a restaurant's day-to-day workflow: a public menu, customer
carts, orders, and role-based access for managers and delivery crew.
Built with Django REST Framework (DRF), Djoser for registration and token
login, and django-filter for filtering.

## Features

- Token authentication with Djoser (`/api/users/`, `/api/token/login/`).
- Three roles driven by Django groups: **Manager**, **Delivery Crew**, **Customer**.
- Menu items with filtering (category, featured, price range), search,
  ordering and pagination.
- Cart that computes prices server-side; one `POST` turns the cart into an order.
- Order lifecycle: managers assign delivery crew, crew flips the status.
- Anonymous and per-user rate limiting.
- 58 automated tests covering every endpoint and role.

## Quick start

Requires [uv](https://docs.astral.sh/uv/) (or Python 3.12 + pip, see below).

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo        # demo users + sample menu
uv run python manage.py runserver
```

Then open <http://127.0.0.1:8000/api/menu-items/> in a browser.

`seed_demo` creates three users, all with password `LittleLemon123!`:

| Username   | Role          |
|------------|---------------|
| `manager`  | Manager       |
| `crew`     | Delivery Crew |
| `customer` | Customer      |

The `Manager` and `Delivery Crew` groups are created by a data migration, so
they always exist. A superuser (`createsuperuser`) is treated as a manager.

<details>
<summary>Without uv</summary>

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate && python manage.py seed_demo && python manage.py runserver
```
</details>

## Authentication

```bash
# Register
curl -X POST http://127.0.0.1:8000/api/users/ \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "Str0ng-Passw0rd!"}'

# Log in -> {"auth_token": "..."}
curl -X POST http://127.0.0.1:8000/api/token/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "Str0ng-Passw0rd!"}'

# Use the token
curl http://127.0.0.1:8000/api/users/me/ -H "Authorization: Token <auth_token>"
```

`/api/users/users/me/` is an alias of `/api/users/me/` (the project brief asks for both).

## Endpoints

All paths are prefixed with `/api/`. "Anyone" includes anonymous visitors.

| Method | Path | Who | Notes |
|--------|------|-----|-------|
| GET | `menu-items/` | Anyone | Filter, search, order, paginate |
| POST | `menu-items/` | Manager | `title`, `price`, `featured`, `category_id` |
| GET | `menu-items/{id}/` | Anyone | |
| PUT, PATCH, DELETE | `menu-items/{id}/` | Manager | DELETE returns 200; 400 if the item is in an order |
| GET | `categories/` | Anyone | |
| POST | `categories/` | Manager | `slug`, `title` |
| GET, PUT, PATCH, DELETE | `categories/{id}/` | Anyone / Manager | |
| GET | `groups/manager/users/` | Manager | List managers |
| POST | `groups/manager/users/` | Manager | `{"username": ...}` or `{"user_id": ...}` -> 201 |
| DELETE | `groups/manager/users/{userId}/` | Manager | 200, or 404 if not a member |
| GET, POST | `groups/delivery-crew/users/` | Manager | Same payloads as above |
| DELETE | `groups/delivery-crew/users/{userId}/` | Manager | |
| GET | `cart/menu-items/` | Customer | My cart |
| POST | `cart/menu-items/` | Customer | `{"menuitem_id": 1, "quantity": 2}`; price is computed |
| DELETE | `cart/menu-items/` | Customer | Empty my cart |
| GET | `orders/` | Any role | Customers: own orders. Crew: assigned orders. Managers: all |
| POST | `orders/` | Customer | Cart -> order + order items, cart emptied; 400 if cart is empty |
| GET | `orders/{id}/` | Owner, assigned crew, Manager | 404 otherwise |
| PUT, PATCH | `orders/{id}/` | Manager | Set `delivery_crew` (must be in the crew group) and `status` |
| PATCH | `orders/{id}/` | Delivery Crew | `{"status": 1}` only; any other field -> 403 |
| DELETE | `orders/{id}/` | Manager | |

Order `status`: `0` = out for delivery, `1` = delivered.

### Filtering, searching, ordering, pagination

```text
/api/menu-items/?category=mains            # id, slug or title
/api/menu-items/?featured=true&price_min=5&price_max=15
/api/menu-items/?search=lemon
/api/menu-items/?ordering=-price           # or price, title
/api/menu-items/?page=2&perpage=5          # default 10, max 50
/api/orders/?status=0&date_from=2026-10-01&delivery_crew=3
```

### Status codes

| Code | When |
|------|------|
| 200 | Success (including DELETE) |
| 201 | Created (menu item, category, cart line, order, group membership) |
| 400 | Validation error, empty cart, duplicate cart line, non-crew user assigned |
| 401 | Missing or invalid token |
| 403 | Authenticated but the role is not allowed |
| 404 | Not found, or not visible to this role |
| 429 | Throttled (`Retry-After` header included) |

### Throttling

Defaults are `20/minute` for anonymous visitors and `100/minute` per
authenticated user. Override with the `THROTTLE_ANON` and `THROTTLE_USER`
environment variables.

## Tests

```bash
uv run python manage.py test
```

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `DJANGO_SECRET_KEY` | dev key | Secret key |
| `DJANGO_DEBUG` | `1` | Set to `0` in production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated |
| `THROTTLE_ANON` / `THROTTLE_USER` | `20/minute` / `100/minute` | Rate limits |

## Project layout

```text
LittleLemon/            Django project (settings, root urls)
LittleLemonAPI/
  models.py             Category, MenuItem, Cart, Order, OrderItem
  serializers.py        Validation and representation
  permissions.py        IsManager, IsDeliveryCrew, IsCustomer, IsManagerOrReadOnly, CanEditOrder
  views.py              Generic views per endpoint
  filters.py            django-filter FilterSets for menu items and orders
  pagination.py         ?page / ?perpage
  urls.py               /api/ routes
  migrations/           Schema + data migration that creates the two groups
  management/commands/  seed_demo
  tests/                One module per resource
```

## License

MIT. See [LICENSE](LICENSE).
