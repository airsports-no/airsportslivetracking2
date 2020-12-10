import logging
import math
from typing import Tuple, Optional
from geopy.distance import geodesic, great_circle
import nvector as nv

R = 6371000  # metres

logger = logging.getLogger(__name__)


def to_rad(value) -> float:
    return value * math.pi / 180


def calculate_distance_lat_lon(start: Tuple[float, float], finish: Tuple[float, float]) -> float:
    """

    :param start:
    :param finish:
    :return: Distance in metres
    """
    # return geodesic(start, finish).km * 1000  # This is the most correct
    return great_circle(start, finish).km * 1000  # This is closer to flight contest
    # This is what flight contest uses
    # latitude_difference = finish[0] - start[0]
    # longitude_difference = finish[1] - start[1]
    # latitude_distance = 60 * latitude_difference
    # longitude_distance = 60 * longitude_difference * math.cos(to_rad((start[0] + finish[0]) / 2))
    # return math.sqrt(latitude_distance ** 2 + longitude_distance ** 2)*1852


def calculate_bearing(start: Tuple[float, float], finish: Tuple[float, float]) -> float:
    la1 = start[0] * math.pi / 180
    lo1 = start[1] * math.pi / 180
    la2 = finish[0] * math.pi / 180
    lo2 = finish[1] * math.pi / 180
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    brng = math.atan2(y, x) * 180 / math.pi
    return (brng + 360) % 360


def calculate_fractional_distance_point_lat_lon(start: Tuple[float, float], finish: Tuple[float, float],
                                                fraction: float) -> Tuple[
    float, float]:
    R = 6371000  # metres
    la1 = start[0] * math.pi / 180
    lo1 = start[1] * math.pi / 180
    la2 = finish[0] * math.pi / 180
    lo2 = finish[1] * math.pi / 180
    distance = calculate_distance_lat_lon(start, finish)
    angularDistance = distance / R
    a = math.sin((1 - fraction) * angularDistance) / math.sin(angularDistance)
    b = math.sin(fraction * angularDistance) / math.sin(angularDistance)
    x = a * math.cos(la1) * math.cos(lo1) + b * math.cos(la2) * math.cos(lo2)
    y = a * math.cos(la1) * math.sin(lo1) + b * math.cos(la2) * math.sin(lo2)
    z = a * math.sin(la1) + b * math.sin(la2)
    finalLatitude = math.atan2(z, math.sqrt(x * x + y * y)) * 180 / math.pi
    finalLongitude = math.atan2(y, x) * 180 / math.pi
    return (finalLatitude, finalLongitude)


def extend_line(start: Tuple[float, float], finish: Tuple[float, float], distance: float) -> Optional[Tuple[
    Tuple[float, float], Tuple[float, float]]]:
    """

    :param start: degrees
    :param finish: degrees
    :param distance: nauticalMiles
    :return:
    """
    if distance == 0:
        return None
    line_length = calculate_distance_lat_lon(start, finish)
    distance_scale = 1852 * distance / (2 * line_length)
    new_finish = calculate_fractional_distance_point_lat_lon(start, finish, 1 + distance_scale)
    new_start = calculate_fractional_distance_point_lat_lon(finish, start, 1 + distance_scale)
    return new_start, new_finish


def line_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
    # Check if none of the lines are of length 0
    if (x1 == x2 and y1 == y2) or (x3 == x4 and y3 == y4):
        return None

    denominator = ((y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1))
    # Lines are parallel
    if denominator == 0:
        return None
    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denominator
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denominator

    # is the intersection along the segments
    if ua < 0 or ua > 1 or ub < 0 or ub > 1:
        return None

    # Return a object with the x and y coordinates of the intersection
    x = x1 + ua * (x2 - x1)
    y = y1 + ua * (y2 - y1)

    return x, y


import pyproj
from pyproj import CRS, Transformer
from shapely.geometry import Point
from shapely.ops import transform
from functools import partial


class Projector:
    def __init__(self, latitude, longitude):
        WGS84 = CRS.from_string('epsg:4326')
        proj4str = '+proj=aeqd +lat_0=%s +lon_0=%s +x_0=0 +y_0=0' % (latitude, longitude)
        AEQD = CRS.from_proj4(proj4str)
        self.to_projection = Transformer.from_crs(WGS84, AEQD, always_xy=True)
        self.from_projection = Transformer.from_crs(AEQD, WGS84, always_xy=True)

    def intersect(self, start1, stop1, start2, stop2):
        start1 = self.to_projection.transform(*reversed(start1))
        stop1 = self.to_projection.transform(*reversed(stop1))
        start2 = self.to_projection.transform(*reversed(start2))
        stop2 = self.to_projection.transform(*reversed(stop2))

        intersection = line_intersect(*start1, *stop1, *start2, *stop2)
        if intersection is None:
            return None
        converted = self.from_projection.transform(*intersection)
        return converted[1], converted[0]


def nv_intersect(start1, stop1, start2, stop2):
    pointA1 = nv.GeoPoint(start1[0], start1[1], degrees=True)
    pointA2 = nv.GeoPoint(stop1[0], stop1[1], degrees=True)
    pointB1 = nv.GeoPoint(start2[0], start2[1], degrees=True)
    pointB2 = nv.GeoPoint(stop2[0], stop2[1], degrees=True)
    pathA = nv.GeoPath(pointA1, pointA2)
    pathB = nv.GeoPath(pointB1, pointB2)
    if pathA == pathB:
        return None
    c = pathA.intersect(pathB)
    c_geo = c.to_geo_point()
    m1 = (c_geo.latitude_deg - start1[0]) / (c_geo.longitude_deg - start1[1])
    m2 = (c_geo.latitude_deg - stop1[0]) / (c_geo.longitude_deg - stop1[1])
    if m1 == m2:
        return c_geo.latitude_deg, c_geo.longitude_deg
    return None


def fraction_of_leg(start, finish, intersect_point):
    return calculate_distance_lat_lon(start, intersect_point) / calculate_distance_lat_lon(start, finish)


def get_heading_difference(heading1, heading2):
    """
    From first heading to 2nd heading
    :param heading1:
    :param heading2:
    :return:
    """
    return (heading2 - heading1 + 540) % 360 - 180


def cross_track_distance(lat1, lon1, lat2, lon2, lat, lon):
    angular_distance13 = calculate_distance_lat_lon((lat1, lon1), (lat, lon)) / R
    first_bearing = calculate_bearing((lat1, lon1), (lat, lon)) * math.pi / 180
    second_bearing = calculate_bearing((lat1, lon1), (lat2, lon2)) * math.pi / 180
    return math.asin(math.sin(angular_distance13) * math.sin(first_bearing - second_bearing)) * R


def along_track_distance(lat1, lon1, lat, lon, cross_track_distance):
    angular_distance13 = calculate_distance_lat_lon((lat1, lon1), (lat, lon)) / R
    try:
        return math.acos(math.cos(angular_distance13) / math.cos(cross_track_distance / R)) * R
    except:
        # try:
        #     logger.exception("Something failed when calculating along track distance: {} {} {}".format(
        #         math.cos(angular_distance13), math.cos(cross_track_distance),
        #         math.cos(angular_distance13) / math.cos(cross_track_distance / R)))
        # except:
        #     logger.exception("Failed even printing the error message")
        return 999999999999
