# Wingz Ride API

DRF API for the Wingz backend assessment - rides, riders/drivers, ride events, all gated to admin
users via JWT. The interesting part isn't the CRUD, it's keeping the ride list endpoint cheap as the
Ride/RideEvent tables grow (see "notes" below).

Stack: Django 5.1, DRF, Postgres, `djangorestframework-simplejwt`, `django-filter`.

## Setup

Needs Python 3.11+ and Docker. If you've already got Postgres running locally on 5432, heads up -
the compose file maps to **5433** on the host instead, specifically to avoid clashing with it.

```bash
python -m venv .venv
.venv\Scripts\activate        # source .venv/bin/activate on mac/linux
pip install -r requirements.txt

cp .env.example .env
docker compose up -d
python manage.py wait_for_db   # postgres in the container takes a sec to accept connections
python manage.py migrate
python manage.py createsuperuser
```

Everything here requires `role=admin` - including creating other users - so make your superuser an
admin right after:

```python
# python manage.py shell
from core.models import User
u = User.objects.get(username="you")
u.role = User.Role.ADMIN
u.save()
```

`python manage.py runserver` and you're up.

## Auth + hitting the API

```bash
curl -X POST http://localhost:8000/api/token/ -H "Content-Type: application/json" \
  -d '{"username": "you", "password": "..."}'
# -> {"access": "...", "refresh": "..."}

curl http://localhost:8000/api/rides/ -H "Authorization: Bearer <access>"
```

`/api/token/refresh/` for refreshing. Every other endpoint requires an admin role, checked fresh
from the DB per request (not from the token - a demoted user's still-valid token shouldn't keep
working).

## Ride list - `GET /api/rides/`

Paginated, `page`/`page_size` (20 default, 100 max). Nests `rider`/`driver` plus flat
`id_rider`/`id_driver`, and a `todays_ride_events` field (last 24h only).

- `status=en-route|pickup|dropoff` and `rider_email=...` to filter
- `sort=pickup_time` (default) or `sort=distance`
- `sort=distance` needs `pickup_lat` + `pickup_lng`; `radius_km` is optional and just narrows the
  candidate set with a lat/lng bounding box before computing exact distance

`GET /api/rides/{id}/` is the same shape but swaps `todays_ride_events` for the full `ride_events`
history - fine to load in full there since it's one ride, not the whole table.

`/api/users/` and `/api/ride-events/` are plain CRUD.

## Notes on the harder requirements

The distance sort (`rides/distance.py`) computes distance DB-side with plain trig
(`Radians`/`Sin`/`Cos`/`ACos`), so it's just another `order_by()` - nothing gets pulled into Python.
No PostGIS, which means no real spatial index for it, so it's an `O(n)` scan+sort under the hood
regardless of page number. `radius_km` gives you a bounding-box prefilter that a plain index on
`(pickup_latitude, pickup_longitude)` can actually use, which softens that a lot. If this needs to be
properly index-accelerated later, `cube`/`earthdistance` + a GiST index is the next lightest step
before reaching for full PostGIS.

Watch out if you touch that math: identical/near-identical coordinates can push the cosine term a
hair past ±1 from floating-point rounding, and Postgres's `ACOS` throws on that. It's clamped with
`Least`/`Greatest` before the `ACos` call - don't remove that.

For `todays_ride_events`: the spec wants nested RideEvents on the list *and* keeps the whole
endpoint at ~2-3 queries no matter how big RideEvent gets. Those two things don't really coexist if
you nest the full history per ride, so `list` only ever prefetches the 24h window
(`Prefetch(..., to_attr="todays_ride_events")`), and `retrieve` gets the full history since that's
bounded to one ride regardless of table size. The `to_attr` name is deliberately not the same as the
real related manager (`events`) - reusing that name would silently fall back to `ride.events.all()`
unfiltered, per row, which is the N+1 the whole thing is trying to avoid.

Query count is asserted, not just claimed - see `assertNumQueries` in `rides/tests/test_views.py`
(3 for list, 2 for retrieve).

Login obviously can't itself require `role=admin` or nobody could ever get a token -
`PublicTokenObtainPairView`/`PublicTokenRefreshView` override that back to `AllowAny`.

`RideListSerializer`'s `rider`/`driver` are nested read-only objects (that's what makes the list
response useful), which means they can't double as the writable fields `create`/`update` need. There's
a separate `RideWriteSerializer` for that (plain FK fields, so a bad rider/driver id comes back as a
normal 400, not a DB IntegrityError). Same idea for `RideEventSerializer` - the nested version used
inside a Ride payload doesn't need `ride` since it's implied by the nesting, but the standalone one at
`/api/ride-events/` does.

## Tests / lint

```bash
python manage.py test
```

Tests live next to what they cover. Ran this before calling it done:

```bash
python -m ruff format core rides config manage.py
python -m ruff check core rides config manage.py
python -m pylint core rides config manage.py   # config in .pylintrc, 10/10
```

## Bonus SQL report

`python manage.py long_trips_report` - count of trips over 1hr pickup-to-dropoff, grouped by month
and driver. Raw SQL (`rides/reports.py`), not ORM, per the assessment.

Duration comes from the `RideEvent` rows (`'Status changed to pickup'` / `'...dropoff'`), not
`Ride.pickup_time`, since that's what the assessment's bonus section is built around.
`ROW_NUMBER()` grabs the earliest pickup and earliest following dropoff per ride so a ride with
duplicate/out-of-order events doesn't skew the count.

```sql
WITH pickup AS (
    SELECT ride_id, created_at,
           ROW_NUMBER() OVER (PARTITION BY ride_id ORDER BY created_at ASC) AS rn
    FROM rides_rideevent
    WHERE description = 'Status changed to pickup'
),
dropoff AS (
    SELECT ride_id, created_at,
           ROW_NUMBER() OVER (PARTITION BY ride_id ORDER BY created_at ASC) AS rn
    FROM rides_rideevent
    WHERE description = 'Status changed to dropoff'
)
SELECT
    DATE_TRUNC('month', p.created_at)  AS month,
    r.driver_id                        AS driver_id,
    u.first_name || ' ' || u.last_name AS driver_name,
    COUNT(*)                           AS trip_count
FROM rides_ride AS r
JOIN pickup   AS p ON p.ride_id = r.id AND p.rn = 1
JOIN dropoff  AS d ON d.ride_id = r.id AND d.rn = 1
JOIN core_user AS u ON u.id = r.driver_id
WHERE d.created_at > p.created_at
  AND EXTRACT(EPOCH FROM (d.created_at - p.created_at)) / 3600.0 > 1
GROUP BY 1, r.driver_id, driver_name
ORDER BY 1, driver_name;
```

## One deliberate deviation from the spec

The spec's table defs use `id_ride`, `id_rider`, etc. This uses normal Django conventions instead -
auto `id` PK, FKs named for what they point to (`rider`, `driver`, `ride`) instead of forcing
`db_column` overrides everywhere. Same data, just reads like a normal Django app instead of a literal
column-for-column port.
