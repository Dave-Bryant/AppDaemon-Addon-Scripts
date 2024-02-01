import appdaemon.plugins.hass.hassapi as hass
#import datetime

# import pymysql.cursors
# import sqlite3
# import os
# import json
from datetime import datetime
from datetime import timedelta
from statistics import mean
import pytz

from influxdb import InfluxDBClient
import math
from eto import ETo, datasets
import pandas as pd


# Hellow World App
#
# Args: xxxxX
#






  
class HelloWorld(hass.Hass):
  def initialize(self):
     self.log("Hello from AppDaemon")
    #  ET= 4.5
    #  ET_calc= 4.25
    #  apply_rain= 0.5
    #  self.log(f'New ET {ET:0.2f} after ET_calc {ET_calc:0.2f} reduced by Rain bucket {(ET-ET_calc):0.2f} amount')
     #self.log(self.list_services(namespace="default"))
     #self.irrigation_entity = self.get_entity("sensor.smart_irrigation_garden")
     #self.irrigation_entity.call_service("smart_irrigation/reset_bucket")
     #self.call_service("smart_irrigation/reset_all_buckets") 
     #self.call_service("smart_irrigation/set_bucket", entityid = "sensor.smart_irrigation_garden", data = 2 )
     # self.log("Reset complete")

     #self.run_every(self.main_routine,"now", 15)
     
     self.run_in(self.load_dataframe1, 0)

  def load_dataframe1(self, *args):
      # Connect to History Database
      
            
      self.run_in(self.main_routine, 0)     
     
  
  def main_routine(self, *args):
    self.log("Bye from AppDaemon") 
    
  