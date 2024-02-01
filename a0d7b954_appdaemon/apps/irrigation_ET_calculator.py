import appdaemon.plugins.hass.hassapi as hass
from influxdb import InfluxDBClient
from eto import ETo, datasets
import pandas as pd
import numpy as np

 
class ET_Calculation(hass.Hass):

    def initialize(self):
        self.log("Start ET Calculation")
        self.debug = False
        self.debug_extra = False
        self.run_without_update = False   ###### FOR TESTING
        
        self.ET = float(self.get_state(self.args["EVAPOTRANSPIRATION"] ))    # lovelace fields
        self.ET_calc = float(self.get_state(self.args["EVAPOTRANSPIRATIONCALC"]))
        self.run_time = float(self.get_state(self.args["IRRIGATIONRUNTIME"]))*60 # convert to seconds
        try:            
            self.rain_tracked = float(self.get_state(self.args["DAILYRAINEVENT"]))  #  Reused             
        except Exception as exc:  
            self.rain_tracked = 0
            self.log(f"Exception is {exc}, Daily rain Event set to 0")              
        finally:            
            pass

        self.z_msl = 430 # elevation these are for ETo
        self.lat = -35.282001
        self.lon = 149.128998
        self.TZ_lon = 143
        self.freq = 'H'

        self.start_time = self.args["ETCALCSTARTTIME"]
        self.area = self.args["AREA"]
        self.sprinkler_number = self.args["SPRINKLERNUMBER"]
        self.sprinkler_half_circle_rate = self.args["SPRINKLERHALFCIRCLERATE"]
        self.max_run_time = self.args["SPRINKLERMAXRUNTIME"]

        try:            
            self.daily_rain = float(self.get_state(self.args["DAILYRAIN"]))  # Sensors             
        except Exception as exc:  
            self.daily_rain = 0
            self.log(f"Exception is {exc}, Daily rain set to 0")              
        finally:            
            pass

        try:            
            self.event_rain = float(self.get_state(self.args["EVENTRAIN"]))  # Sensors             
        except Exception as exc:  
            self.event_rain = 0
            self.log(f"Exception is {exc}, Event rain set to 0")              
        finally:            
            pass
        

        self.max_bucket_size = self.args["MAXBUCKETSIZE"]

        self.PASS = 0

        if not self.run_without_update:self.run_daily(self.main_routine, self.start_time)  
        if self.run_without_update: self.run_in(self.main_routine, 0)
        #self.run_in(self.main_routine, 0)
    def main_routine(self, *args):  
        
        self.PASS = self.PASS + 1 
        self.ET , self.PASS = self.Calculate_ET_for_the_day(self.ET, self.z_msl,self.lat,self.lon,self.TZ_lon,self.freq, self.PASS)        
        self.log(f"ET is: {self.ET:0.2f}") 
        self.set_value("input_number.daily_et", self.ET)       
        self.run_time = self.Calculate_run_time(self.ET,self.area,self.sprinkler_number,self.sprinkler_half_circle_rate,self.max_run_time)
        self.log(f"run time is: {self.run_time/60:0.2f} mins")
        self.set_value("input_number.lawn_watering_time", int(self.run_time/60))         
        if self.PASS >= 2: self.run_in(self.main_routine, 1200)  # 20 mins run again if an exception

    # METHODS.
  
    def Calculate_ET_for_the_day(self,*kwarg):
    # Connect to Influx History Database
        try:
            self.conn = InfluxDBClient("10.0.0.55", 8086, "homeassistant", "david", "homeassistant")   
            self.log("Connection to influxdb was succesfull")  

            # Execute the query and return a table
            self.table = self.conn.query(
                    query="SELECT mean(\"value\") FROM \"°C\" WHERE (\"entity_id\"::tag = 'temp') AND time >= now() - 23h and time <= now() GROUP BY time(1h) fill(null)"
                    )   
            self.dat = self.table.raw['series'][0]['values']   
            self.df1 = pd.DataFrame(self.dat, columns=[ 'time', 'T_mean'])  
                    
            if self.debug: self.log(self.df1)

            self.table = self.conn.query(
                    query="SELECT mean(\"value\") FROM \"%\" WHERE (\"entity_id\"::tag = 'humidity') AND time >= now() - 23h and time <= now() GROUP BY time(1h) fill(null)"
                    )   
            self.dat = self.table.raw['series'][0]['values']   
            self.df2 = pd.DataFrame(self.dat, columns=[ 'time', 'RH_mean'])
            
            if self.debug:self.log(self.df2)

            self.table = self.conn.query(
                    query="SELECT mean(\"value\") FROM \"°C\" WHERE (\"entity_id\"::tag = 'low_temperature_per_hour') AND time >= now() - 23h and time <= now() GROUP BY time(1h) fill(null)"
                    ) 
            
            self.dat = self.table.raw['series'][0]['values']   
            self.df3 = pd.DataFrame(self.dat, columns=[ 'time', 'T_min'])
            
            if self.debug:self.log(self.df3)

            self.table = self.conn.query(
                    query="SELECT mean(\"value\") FROM \"°C\" WHERE (\"entity_id\"::tag = 'high_temperature_per_hour') AND time >= now() - 23h and time <= now() GROUP BY time(1h) fill(null)"
                    )   
            self.dat = self.table.raw['series'][0]['values']   
            self.df4 = pd.DataFrame(self.dat, columns=[ 'time', 'T_max'])
            
            if self.debug:self.log(self.df4)

            self.table = self.conn.query(
                    query="SELECT mean(\"value\") FROM  \"hPa\" WHERE (\"entity_id\"::tag = 'baromabs') AND time >= now() - 23h and time <= now() GROUP BY time(1h) fill(null)"
                    )   
            self.dat = self.table.raw['series'][0]['values']   
            self.df5 = pd.DataFrame(self.dat, columns=[ 'time', 'P'])
            self.df5['P'] = self.df5['P']/10 # converting HPa to kPa

            if self.debug:self.log(self.df5)

            self.table = self.conn.query(
                    query="SELECT mean(\"value\") FROM \"°C\" WHERE (\"entity_id\"::tag = 'dewpoint') AND time >= now() - 23h and time <= now() GROUP BY time(1h) fill(null)"
                    )   
            self.dat = self.table.raw['series'][0]['values']   
            self.df6 = pd.DataFrame(self.dat, columns=[ 'time', 'T_dew'])
            
            if self.debug:self.log(self.df6)

            self.table = self.conn.query(
                    query="SELECT mean(\"value\") FROM \"km/h\" WHERE (\"entity_id\"::tag = 'windspeed') AND time >= now() - 23h and time <= now() GROUP BY time(1h) fill(null)"
                    )   
            self.dat = self.table.raw['series'][0]['values']   
            self.df7 = pd.DataFrame(self.dat, columns=[ 'time', 'U_z'])

            if self.debug:self.log(self.df7)

            self.table = self.conn.query(
                    query="SELECT mean(\"value\") FROM \"W/m²\" WHERE (\"entity_id\"::tag = 'solarradiation') AND time >= now() - 23h and time <= now() GROUP BY time(1h) fill(null)"
                    )   
            self.dat = self.table.raw['series'][0]['values']              
            self.df8 = pd.DataFrame(self.dat, columns=[ 'time', 'R_s'])
            self.df8['R_s'] = self.df8['R_s']*0.0036  # converting W/m2 to MJ/m2 per hour
            
            if self.debug:self.log(self.df8)

            self.table = self.conn.query(
                    query="SELECT mean(\"value\") FROM \"%\" WHERE (\"entity_id\"::tag = 'high_relative_humidity_per_hour') AND time >= now() - 23h and time <= now() GROUP BY time(1h) fill(null)"
                    )   
            self.dat = self.table.raw['series'][0]['values']   
            self.df9 = pd.DataFrame(self.dat, columns=[ 'time', 'RH_max'])
            
            if self.debug:self.log(self.df9)

            self.table = self.conn.query(
                    query="SELECT mean(\"value\") FROM \"%\" WHERE (\"entity_id\"::tag = 'low_relative_humidity_per_hour') AND time >= now() - 23h and time <= now() GROUP BY time(1h) fill(null)"
                    )   
            self.dat = self.table.raw['series'][0]['values']   
            self.df10 = pd.DataFrame(self.dat, columns=[ 'time', 'RH_min'])
            
            if self.debug:self.log(self.df10)

            self.df1 = pd.merge(self.df1, self.df2, on='time', how='outer')
            self.df1 = pd.merge(self.df1, self.df3, on='time', how='outer')
            self.df1 = pd.merge(self.df1, self.df4, on='time', how='outer')
            self.df1 = pd.merge(self.df1, self.df5, on='time', how='outer')
            self.df1 = pd.merge(self.df1, self.df6, on='time', how='outer')
            self.df1 = pd.merge(self.df1, self.df7, on='time', how='outer')
            self.df1 = pd.merge(self.df1, self.df8, on='time', how='outer')
            self.df1 = pd.merge(self.df1, self.df9, on='time', how='outer')
            self.df1 = pd.merge(self.df1, self.df10, on='time', how='outer')


            self.df1.time = pd.to_datetime(self.df1.time)
            self.df1.set_index('time', inplace=True)
            self.df1 = self.df1.fillna(0)

            if self.debug_extra:self.log(self.df1)

            self.et1 = ETo()
            
            self.et1.param_est(self.df1, self.freq, self.z_msl, self.lat, self.lon, self.TZ_lon)
                       
            if self.debug:self.log(self.et1.ts_param)
            
            self.eto1 = self.et1.eto_fao(interp='linear',maxgap=6)
            self.ET_calc = self.eto1['ETo_FAO_interp_mm'].sum()
            self.set_value("input_number.daily_calc_et", self.ET_calc)
            self.log(f"ET sucessfully calculated as {self.ET_calc:0.2f}")

            if self.debug_extra:self.log(self.eto1)

                # RAIN ROUTINE

            self.rain_tracked = float(self.get_state('input_number.daily_rain_event'))
            self.daily_rain = float(self.get_state(self.args["DAILYRAIN"]))  
            self.event_rain = float(self.get_state(self.args["EVENTRAIN"]))
            self.rained  = max(self.daily_rain, self.event_rain, self.rain_tracked)   # check if it has rained
            if self.rained != 0:                                   # yep its rained                
                if self.daily_rain == self.rained:
                    self.ET = self.Apply_rain_to_ET(self.daily_rain,self.ET_calc,self.ET,self.max_bucket_size) # Rain so far
                elif self.event_rain == self.rained:
                    self.ET = self.Apply_rain_to_ET(self.event_rain,self.ET_calc,self.ET,self.max_bucket_size) # last 24 hr rain event 
                else:
                    self.ET = self.Apply_rain_to_ET(self.rain_tracked,self.ET_calc,self.ET,self.max_bucket_size) # rain we are counting down
            else:
                 self.ET = self.ET_calc  

            self.PASS = 0 # turn off exception processing      

        except Exception as exc:  
            self.PASS = self.PASS + 1 
            self.ET = 2
            self.log(f"Exception is {exc}, Pass number: {self.PASS}")              
        finally:
            return self.ET, self.PASS
        
    def Apply_rain_to_ET(self,apply_rain,ET_calc,ET,max_bucket_size): 
        if apply_rain > max_bucket_size:                      
                     self.log(f'Rain bucket set from {apply_rain:0.2f} to maximum {max_bucket_size:0.2f} mm') 
                     apply_rain = max_bucket_size
                
        if apply_rain >= ET_calc: 
                ET =  0   # rain not needed
                self.log(f'ET set to 0 as Rain bucket {apply_rain:0.2f} exceeds (or equals) ET_calc {ET_calc:0.2f}') 
                apply_rain = apply_rain - ET_calc
                self.log(f'Rain bucket decreased by ET_calc and set to {apply_rain:0.2f} mm')  
        else:   
                ET = ET_calc - apply_rain
                self.log(f'New ET {ET:0.2f} after ET_calc {ET_calc:0.2f} reduced by Rain bucket {(ET_calc-ET):0.2f} amount') 
                #apply_rain = 0
        
        if not self.run_without_update: self.set_value("input_number.daily_rain_event", round(apply_rain, 2)) 
        return ET

    def Calculate_run_time(self,*kwarg):
        self.throughput = self.sprinkler_number * self.sprinkler_half_circle_rate #m3/hr      
        self.precipitation_rate = self.throughput * 1000 / self.area # mm/hr 
        self.run_time = self.ET/self.precipitation_rate*3600  #seconds 
        if self.run_time > self.max_run_time: 
                self.run_time = 1800 
                self.log('Maximum run time set')        
        return self.run_time
    
    
    


    









