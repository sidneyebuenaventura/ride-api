from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from core.models import User
from rides.models import Ride, RideEvent


class RideViewSetTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="x",
            role=User.Role.ADMIN,
        )
        self.rider_a = User.objects.create_user(
            username="rider_a",
            email="a@example.com",
            password="x",
            role=User.Role.RIDER,
        )
        self.rider_b = User.objects.create_user(
            username="rider_b",
            email="b@example.com",
            password="x",
            role=User.Role.RIDER,
        )
        self.driver = User.objects.create_user(
            username="driver",
            email="d@example.com",
            password="x",
            role=User.Role.DRIVER,
        )

        now = timezone.now()
        # San Francisco pickup, closer to our test query point
        self.near_ride = self._make_ride(
            self.rider_a,
            Ride.Status.EN_ROUTE,
            37.7749,
            -122.4194,
            now - timedelta(hours=1),
        )
        # New York pickup, far from our test query point
        self.far_ride = self._make_ride(
            self.rider_b,
            Ride.Status.DROPOFF,
            40.7128,
            -74.0060,
            now - timedelta(hours=2),
        )

        RideEvent.objects.create(
            ride=self.near_ride, description="Status changed to pickup"
        )
        stale = RideEvent.objects.create(
            ride=self.near_ride, description="Status changed to dropoff"
        )
        RideEvent.objects.filter(pk=stale.pk).update(
            created_at=now - timedelta(hours=48)
        )

        self.client = APIClient()
        self.list_url = reverse("ride-list")

    def _make_ride(self, rider, status_, lat, lng, pickup_time):
        return Ride.objects.create(
            status=status_,
            rider=rider,
            driver=self.driver,
            pickup_latitude=lat,
            pickup_longitude=lng,
            dropoff_latitude=lat,
            dropoff_longitude=lng,
            pickup_time=pickup_time,
        )

    def test_anonymous_request_is_unauthorized(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_request_is_forbidden(self):
        self.client.force_authenticate(self.rider_a)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_gets_paginated_list(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertIn("results", response.data)

    def test_filter_by_status(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.list_url, {"status": Ride.Status.DROPOFF})
        ids = [r["id"] for r in response.data["results"]]
        self.assertEqual(ids, [self.far_ride.pk])

    def test_filter_by_rider_email(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.list_url, {"rider_email": "a@example.com"})
        ids = [r["id"] for r in response.data["results"]]
        self.assertEqual(ids, [self.near_ride.pk])

    def test_sort_by_pickup_time_defaults_to_most_recent_first(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.list_url, {"sort": "pickup_time"})
        ids = [r["id"] for r in response.data["results"]]
        self.assertEqual(ids, [self.near_ride.pk, self.far_ride.pk])

    def test_sort_by_distance_orders_nearest_first(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(
            self.list_url,
            {"sort": "distance", "pickup_lat": "37.7749", "pickup_lng": "-122.4194"},
        )
        ids = [r["id"] for r in response.data["results"]]
        self.assertEqual(ids, [self.near_ride.pk, self.far_ride.pk])
        self.assertLess(
            response.data["results"][0]["distance"],
            response.data["results"][1]["distance"],
        )

    def test_sort_by_distance_without_coordinates_is_a_bad_request(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.list_url, {"sort": "distance"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pagination_stays_stable_across_pages_when_sorted_by_distance(self):
        """The spec calls this out explicitly - sorting by distance can't
        break pagination. A third ride (London) makes 3 rides total, so a
        page_size of 2 forces an actual page boundary to check against."""
        third_ride = self._make_ride(
            self.rider_b, Ride.Status.EN_ROUTE, 51.5074, -0.1278, timezone.now()
        )
        self.client.force_authenticate(self.admin)
        params = {
            "sort": "distance",
            "pickup_lat": "37.7749",
            "pickup_lng": "-122.4194",
            "page_size": 2,
        }
        page1 = self.client.get(self.list_url, params)
        page2 = self.client.get(self.list_url, {**params, "page": 2})

        ids_page1 = [r["id"] for r in page1.data["results"]]
        ids_page2 = [r["id"] for r in page2.data["results"]]
        all_ids = ids_page1 + ids_page2

        self.assertEqual(len(ids_page1), 2)
        self.assertEqual(len(ids_page2), 1)
        self.assertEqual(
            set(all_ids), {self.near_ride.pk, self.far_ride.pk, third_ride.pk}
        )
        self.assertEqual(
            len(set(all_ids)), 3, "same ride shouldn't appear on two pages"
        )

    def test_todays_ride_events_excludes_events_older_than_24h(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.list_url, {"status": Ride.Status.EN_ROUTE})
        events = response.data["results"][0]["todays_ride_events"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["description"], "Status changed to pickup")

    def test_list_endpoint_query_count_stays_flat(self):
        """Pins the perf requirement: rides + rider/driver join (1) +
        prefetched todays_ride_events (1) + pagination COUNT (1) = 3,
        regardless of how many rides or ride events exist."""
        self.client.force_authenticate(self.admin)
        with self.assertNumQueries(3):
            self.client.get(self.list_url)

    def test_retrieve_query_count_stays_flat(self):
        self.client.force_authenticate(self.admin)
        detail_url = reverse("ride-detail", args=[self.near_ride.pk])
        with self.assertNumQueries(2):
            self.client.get(detail_url)

    def test_create_ride_sets_rider_and_driver(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url,
            {
                "status": Ride.Status.EN_ROUTE,
                "rider": self.rider_a.id,
                "driver": self.driver.id,
                "pickup_latitude": 1.0,
                "pickup_longitude": 2.0,
                "dropoff_latitude": 3.0,
                "dropoff_longitude": 4.0,
                "pickup_time": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Ride.objects.get(pk=response.data["id"])
        self.assertEqual(created.rider_id, self.rider_a.id)
        self.assertEqual(created.driver_id, self.driver.id)

    def test_create_ride_with_nonexistent_rider_is_a_bad_request_not_a_crash(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url,
            {
                "status": Ride.Status.EN_ROUTE,
                "rider": 999999,
                "driver": self.driver.id,
                "pickup_latitude": 1.0,
                "pickup_longitude": 2.0,
                "dropoff_latitude": 3.0,
                "dropoff_longitude": 4.0,
                "pickup_time": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RideEventViewSetTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="re_admin",
            email="re_admin@example.com",
            password="x",
            role=User.Role.ADMIN,
        )
        rider = User.objects.create_user(
            username="re_rider", email="re_rider@example.com", password="x"
        )
        driver = User.objects.create_user(
            username="re_driver", email="re_driver@example.com", password="x"
        )
        self.ride = Ride.objects.create(
            status=Ride.Status.EN_ROUTE,
            rider=rider,
            driver=driver,
            pickup_latitude=0,
            pickup_longitude=0,
            dropoff_latitude=0,
            dropoff_longitude=0,
            pickup_time=timezone.now(),
        )
        self.client = APIClient()
        self.list_url = reverse("rideevent-list")

    def test_create_ride_event_attaches_to_the_given_ride(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url,
            {"ride": self.ride.id, "description": "Status changed to pickup"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = RideEvent.objects.get(pk=response.data["id"])
        self.assertEqual(event.ride_id, self.ride.id)

    def test_create_ride_event_with_nonexistent_ride_is_a_bad_request_not_a_crash(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.list_url,
            {"ride": 999999, "description": "Status changed to pickup"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
