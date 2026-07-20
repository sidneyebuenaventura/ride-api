"""Raw-SQL bonus report: count of trips over 1hr pickup-to-dropoff,
grouped by month and driver. Deliberately raw SQL, not ORM, per the
assessment's "Bonus - SQL" section.

Duration is derived from RideEvent timestamps (the two events
'Status changed to pickup' / 'Status changed to dropoff'), not from
Ride.pickup_time, since that's what the spec's bonus section is built
around. ROW_NUMBER() picks the earliest pickup/dropoff event per ride
so a ride with duplicate or out-of-order events doesn't skew the count.
"""

from django.db import connection

LONG_TRIPS_BY_MONTH_AND_DRIVER_SQL = """
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
    DATE_TRUNC('month', p.created_at)          AS month,
    r.driver_id                                 AS driver_id,
    u.first_name || ' ' || u.last_name          AS driver_name,
    COUNT(*)                                     AS trip_count
FROM rides_ride AS r
JOIN pickup   AS p ON p.ride_id = r.id AND p.rn = 1
JOIN dropoff  AS d ON d.ride_id = r.id AND d.rn = 1
JOIN core_user AS u ON u.id = r.driver_id
WHERE d.created_at > p.created_at
  AND EXTRACT(EPOCH FROM (d.created_at - p.created_at)) / 3600.0 > 1
GROUP BY 1, r.driver_id, driver_name
ORDER BY 1, driver_name;
"""


def long_trips_by_month_and_driver():
    with connection.cursor() as cursor:
        cursor.execute(LONG_TRIPS_BY_MONTH_AND_DRIVER_SQL)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
