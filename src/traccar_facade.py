import datetime
import logging
from typing import List, Dict, TYPE_CHECKING, Optional, Tuple

import requests
from requests import Session

if TYPE_CHECKING:
    from display.models import TraccarCredentials

logger = logging.getLogger(__name__)


class Traccar:
    def __init__(self, protocol, address, token):
        self.protocol = protocol
        self.address = address
        self.token = token
        self.base = "{}://{}".format(self.protocol, self.address)
        self.session = self.get_authenticated_session()
        self.device_map = None

    @classmethod
    def create_from_configuration(cls, configuration: "TraccarCredentials") -> "Traccar":
        return cls(configuration.protocol, configuration.address, configuration.token)

    def get_authenticated_session(self) -> Session:
        session = requests.Session()
        string = self.base + "/api/session?token={}".format(self.token)
        response = session.get(string)
        if response.status_code != 200:
            raise Exception("Failed authenticating session: {}".format(response.text))
        return session

    def get_positions_for_device_id(self, device_id: int, start_time: datetime.datetime,
                                    finish_time: datetime.datetime) -> List[Dict]:
        response = self.session.get(self.base + "/api/positions",
                                    params={"deviceId": device_id, "from": start_time.isoformat(),
                                            "to": finish_time.isoformat()})
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed fetching positions for device {device_id}, {response.text}")

    def update_and_get_devices(self) -> List:
        return self.session.get(self.base + "/api/devices").json()

    def delete_device(self, device_id):
        response = self.session.delete(self.base + "/api/devices/{}".format(device_id))
        print(response)
        print(response.text)
        return response.status_code == 204

    def get_groups(self) -> List[Dict]:
        response = self.session.get(self.base + "/api/groups")
        if response.status_code == 200:
            return response.json()

    def create_group(self, group_name) -> Dict:
        response = self.session.post(self.base + "/api/groups", json={"name": group_name})
        if response.status_code == 200:
            return response.json()

    def get_shared_group_id(self):
        groups = self.get_groups()
        for group in groups:
            if group["name"] == "GlobalDevices":
                return group["id"]
        return self.create_group("GlobalDevices")["id"]

    def create_device(self, device_name, identifier):
        response = self.session.post(self.base + "/api/devices", json={"uniqueId": identifier, "name": device_name,
                                                                       "groupId": self.get_shared_group_id()})
        print(response)
        print(response.text)
        if response.status_code == 200:
            return response.json()

    def add_device_to_shared_group(self, deviceId):
        response = self.session.put(self.base + f"/api/devices/{deviceId}/",
                                    json={"groupId": self.get_shared_group_id(), "id": deviceId})
        if response.status_code == 200:
            return True

    def get_device(self, identifier) -> Optional[Dict]:
        response = self.session.get(self.base + "/api/devices/?uniqueId={}".format(identifier))
        if response.status_code == 200:
            devices = response.json()
            try:
                return devices[0]
            except IndexError:
                return None
        return None

    def update_device_name(self, device_name: str, identifier: str) -> bool:
        existing_device = self.get_device(identifier)
        logger.info(f" Found existing device {existing_device}")
        if existing_device is None:
            logger.warning("Failed fetching assumed to be existing device {}".format(identifier))
            return False
        key = existing_device["id"]
        response = self.session.put(self.base + f"/api/devices/{key}/",
                                    json={"name": device_name, "id": key, "uniqueId": identifier})
        if response.status_code != 200:
            logger.error(f"Failed updating device name because of: {response.status_code} {response.text}")
            return False
        logger.info(f"Updated device name for {identifier} to {device_name}")
        return True

    def get_or_create_device(self, device_name, identifier) -> Tuple[Dict, bool]:
        existing_device = self.get_device(identifier)
        if existing_device is None:
            return self.create_device(device_name, identifier), True
        return existing_device, False

    def delete_all_devices(self):
        devices = self.update_and_get_devices()
        for item in devices:
            self.delete_device(item["id"])
        return devices

    def get_device_map(self) -> Dict:
        self.device_map = {item["id"]: item["uniqueId"] for item in self.update_and_get_devices()}
        return self.device_map
