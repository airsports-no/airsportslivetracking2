import os


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "live_tracking_map.settings")
    import django

    django.setup()

from influx_facade import InfluxFacade


influx = InfluxFacade()
print(influx.get_number_of_positions_in_database())
