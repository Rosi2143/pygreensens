# check https://drive.google.com/file/d/1DgJpJ1I9FXb7Ux3_eD-xekhu7_ZnX0eg/view
# official API documentation

import requests
import urllib3
import datetime
import os

urllib3.disable_warnings()
import json
from datetime import date

verbose = False

class GreensensSensor:
    def __init__(self, json_struct: dict):
        if verbose : print (json_struct)
        self._sensorID    = json_struct["sensorID"]
        print (f"create sensor: {self._sensorID}")
        self._id          = int(json_struct["id"])
        self._isReset     = bool(json_struct["isReset"])
        self._plantId     = int(json_struct["plantId"])
        self._link        = json_struct["link"]
        self._plantNameEN = str(json_struct["plantNameEN"])
        self._plantNameDE = str(json_struct["plantNameDE"])
        self._plantNameLA = str(json_struct["plantNameLA"])
        self._date        = datetime.datetime.fromtimestamp(json_struct["lastConnection"])
        if not self._isReset: self._chargeLevel = int(json_struct["chargeLevel"])
        self._data        = json_struct

    def isSensorActive(self):
        if verbose: print (f"reset = {self._isReset}")
        return not self._isReset

    def return_data(self, onlyActive=False):
        return self._data

    def getSensorID(self, onlyActive=False):
        return self._sensorID


class GreensensNotification:
    def __init__(self, json_struct: dict):
        if verbose : print (json_struct)
        self._date        = datetime.datetime.fromtimestamp(json_struct["date"])
        self._message     = str(json_struct["message"])
        print (f"create notification: {self._message}")
        if json_struct["plantModel"] != None:
            self._sensorID    = json_struct["plantModel"]["sensorID"]
            self._plantId     = json_struct["plantModel"]["plantId"]
        else:
            self._sensorID    = 0
            self._plantId     = 0

    def print(self):
        return str(self._date) + "::" + self._message

class GreensensHub:
    def __init__(self, name: str):
        print (f"create Hub: {name}")
        self._name = name
        self._sensorList = []

    def addSensor(self, sensor: GreensensSensor):
        self._sensorList.append(sensor)

    def return_num_of_sensors(self, onlyActive=False):
        numOfSensors = 0
        for sensor in self._sensorList:
            if sensor.isSensorActive() or not onlyActive:
                numOfSensors += 1
        return numOfSensors

    def return_data(self, onlyActive=False):
        data = {}
        for sensor in self._sensorList:
            if sensor.isSensorActive() or not onlyActive:
                data.update(sensor.return_data())
        return data

    def return_sensors(self, onlyActive=False):
        """Return sensor data"""
        data = []
        for sensor in self._sensorList:
            if sensor.isSensorActive() or not onlyActive:
                data.append(sensor.getSensorID())
        return data

class GreensensApi:
    def __init__(self, username: str, password: str):
        self._user = username
        self._pass = password
        self._host = "https://api.greensens.de/api"
        self.s = requests.Session()
        self._at = None
        self._atd = None
        self._error = "OK"
        self.authenticate()

        self._bearer = f"Bearer {self._at}"
        self._headers = {"Content-Type": "application/json"}

        self._hubList = []
        self._notificationList = []

        self._notifications = None
        self._num_of_notifications = 0

        self.update()

    def return_is_authenticated(self):
        return (self._at != None)

    def return_last_error(self):
        return self._error

    def return_data(self, onlyActive=False):
        """Return sensor data"""
        data = {}
        self.update()
        for hub in self._hubList:
            data.update(hub.return_data(onlyActive))

        return data

    def return_sensors(self, onlyActive=False):
        """Return sensor data"""
        data = []
        for hub in self._hubList:
            data += hub.return_sensors(onlyActive)
        return data

    def return_notifications(self):
        """Return notifications data"""
        data = ""
        self.get_notification()
        for notification in self._notificationList:
            data += notification.print() + os.linesep

        return data

    def update(self):
        """Update sensor data"""
        self._data = self.get_sensordata()

    ## HTTP REQUEST ##
    def get_sensordata(self):
        if self._at != None:
            """Make a request."""
            url = f"{self._host}/plants"
            self.update_access_token()
            headers = self._headers
            headers["authorization"] = self._bearer
            data = self.s.get(
                url, headers=headers, verify=False, timeout=10
            )
            if data.status_code == 200:
                hubs = data.json()["data"]["registeredHubs"]
                new_data = {}
                self._hubList.clear()
                for hub in hubs:
                    hub_obj = GreensensHub(hub["name"])
                    for sensor in hub["plants"]:
                        sensor_obj = GreensensSensor(sensor)
                        hub_obj.addSensor(sensor_obj)
                        new_data[sensor["sensorID"]] = sensor
                    self._hubList.append(hub_obj)
                self._error = "OK"
                return new_data
            else:
                self._error = f"HTTP error: " + str(data.status_code) + " for " + data.request.url
                return self._data

    ## HTTP REQUEST ##
    def get_notification(self):
        if self._at != None:
            """Make a request."""
            url = f"{self._host}/users/notifications"
            self.update_access_token()
            headers = self._headers
            headers["authorization"] = self._bearer
            data = self.s.get(
                url, headers=headers, verify=False, timeout=10
            )
            if data.status_code == 200:
                notifications = data.json()["data"]["notifications"]
                self._num_of_notifications = len(notifications)
                for notification in notifications:
                    self._notificationList.append(GreensensNotification(notification))
                self._error = "OK"
                return
            else:
                self._error = f"HTTP error: " + str(data.status_code) + " for " + data.request.url
                return

    ## AUTH ##
    def authenticate(self):
        url = f"{self._host}/users/authenticate"
        payload = json.dumps({"login": self._user, "password": self._pass})
        response = self.s.post(
            url, headers={"Content-Type": "application/json"}, data=payload, timeout=10
        )
        if response.json()["data"] != None:
            token = response.json()["data"]["token"]
            auth_date = date.today()
            self._at = token
            self._atd = auth_date
        else:
            self._error = response.json()["errors"]

    def update_access_token(self):
        if self._at == None:
            self.authenticate()
        tokenage = date.today() - self._atd
        if tokenage.days > 4:
            self.authenticate()

    def return_num_of_hubs(self):
        return len(self._hubList)

    def return_num_of_sensors(self, onlyActive=False):
        numOfSensors = 0
        for hub in self._hubList:
            numOfSensors += hub.return_num_of_sensors(onlyActive)
        return numOfSensors

    def return_num_of_notifications(self):
        return self._num_of_notifications

##===============================##
