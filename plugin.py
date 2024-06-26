# Volvo API plugin
#
# Author: akamming
#
"""
<plugin key="Volvo" name="Volvo API" author="akamming" version="0.1.0" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://github.com/akamming/Domoticz_VolvoRecharge_Plugin">
    <description>
        <h2>Volvo API plugin</h2><br/>
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>doors, windows and lock status, including locking and unlocking of doors (https://developer.volvocars.com/apis/connected-vehicle/endpoints/doors-windows-locks/)</li>
            <li>start/stop climatisation (https://developer.volvocars.com/apis/connected-vehicle/endpoints/climate/)</li>
            <li>Warnings (https://developer.volvocars.com/apis/connected-vehicle/v2/endpoints/warnings/)</li>
            <li>Diagnostics (https://developer.volvocars.com/apis/connected-vehicle/v2/endpoints/diagnostics/)</li>
            <li>Engine information (https://developer.volvocars.com/apis/connected-vehicle/v2/endpoints/engine/)</li>
        </ul>
        <h3>Configuration</h3>
        <ul style="list-style-type:square">
            <li>Use your Volvo on Call Username/password, which is linked to your vehicle.</li>
            <li>Register an app on https://developer.volvocars.com/apis/docs/getting-started/ and copy/past the primary app key in the config below</li>
            <li>Optional: Set a VIN if you connected more than one car to your volvo account. If empty the plugin will use the 1st car attached to your Volvo account</li>
            <li>Set an update interval. If you don't pay Volvo for the API, you're only allowed to do 10.000 calls per day.. so make sure not to set the update interval too high. The plugin does several calles per interval.</li>
        </ul>
    </description>
    <params>
        <param field="Username" label="Volvo On Call Username" required="true"/>
        <param field="Password" label="Volvo On Call Password" required="true" password="true"/>
        <param field="Mode1" label="Primary VCC API Key" required="true"/>
        <param field="Mode2" label="update interval in secs" required="true" default="90"/>
        <param field="Mode3" label="VIN (optional)"/>
        <param field="Mode4" label="FuelType">
            <options>
                <option label="Electric"/>
                <option label="Petrol/Electric (Plugin-Hybird)"/>
                <option label="Petrol"/>
                <option label="Diesel"/>
                <option label="None"/>
            </options>
        </param>
        <param field="Mode5" label="ABRP apikey:token (optional)"/>
        <param field="Mode6" label="Debug" width="150px">
            <options>
                <option label="None" value="0"  default="true" />
                <option label="Python Only" value="2"/>
                <option label="Basic Debugging" value="62"/>
                <option label="Basic+Messages" value="126"/>
                <option label="Queue" value="128"/>
                <option label="Connections Only" value="16"/>
                <option label="Connections+Queue" value="144"/>
                <option label="All" value="-1"/>
            </options>
        </param>
    </params>

</plugin>
"""
#needed modules
import DomoticzEx as Domoticz
import requests
import json
import datetime
from datetime import timezone
from datetime import datetime
import time
from math import sin, cos, sqrt, atan2, radians

#Constants
TIMEOUT=10 #timeout for API requests
MINTIMEBETWEENLOGINATTEMPTS=600 #10 mins

#global vars
abrp_api_key=None
abrp_token=None
vocuser=None
vocpass=None
vccapikey=None
access_token=None
refresh_token=None
expirytimestamp=None
updateinterval=None
lastupdate=None
vin=None
debugging=False
info=False
climatizationactionid=None
climatizationstoptimestamp=time.time()
lastloginattempttimestamp=time.time()-MINTIMEBETWEENLOGINATTEMPTS

#Device Numbers
REMAININGRANGE=1
FULLRANGE=2
BATTERYCHARGELEVEL=3
CHARGINGCONNECTIONSTATUS=4
CHARGINGSYSTEMSTATUS=5
ESTIMATEDCHARGINGTIME=6
CLIMATIZATION=7
CARLOCKED=8
HOOD=9
TAILGATE=10
FRONTLEFTDOOR=11
FRONTRIGHTDOOR=12
REARLEFTDOOR=13
REARRIGHTDOOR=14
FRONTLEFTWINDOW=15
FRONTRIGHTWINDOW=16
REARLEFTWINDOW=17
REARRIGHTWINDOW=18
ESTIMATEDEFFICIENCY=19
ABRPSYNC=20
ODOMETER=21
TANKLID=22
SUNROOF=23
FRONTRIGHTTYREPRESSURE=24
FRONTLEFTTYREPRESSURE=25
REARLEFTTYREPRESSURE=26
REARRIGHTTYREPRESSURE=27
SERVICESTATUS=28
ENGINEHOURSTOSERVICE=29
KMTOSERVICE=30
MONTHSTOSERVICE=31
LONGITUDE=32
LATTITUDE=33
ALTITUDE=34
HEADING=35
DISTANCE2HOME=36
ENGINERUNNING=37
OILLEVEL=38
ENGINECOOLANTLEVEL=39
WASHERFLUIDLEVEL=40
BRAKELIGHTCENTERWARNING=41
BRAKELIGHTLEFTWARNING=42
BRAKELIGHTRIGHTWARNING=43
FOGLIGHTFRONTWARNING=44
FOGLIGHTREARWARNING=45
POSITIONLIGHTFRONTLEFTWARNING=46
POSITIONLIGHTFRONTRIGHTWARNING=47
POSITIONLIGHTREARLEFTWARNING=48
POSITIONLIGHTREARRIGHTWARNING=49
HIGHBEAMLEFTWARNING=50
HIGHBEAMRIGHTWARNING=51
LOWBEAMLEFTWARNING=52
LOWBEAMRIGHTWARNING=53
DAYTIMERUNNINGLIGHTLEFTWARNING=54
DAYTIMERUNNINGLIGHTRIGHTWARNING=55
TURNINDICATIONFRONTLEFTWARNING=56
TURNINDICATIONFRONTRIGHTWARNING=57
TURNINDICATIONREARLEFTWARNING=58
TURNINDICATIONREARRIGHTWARNING=59
REGISTRATIONPLATELIGHTWARNING=60
SIDEMARKLIGHTSWARNING=61
HAZARDLIGHTSWARNING=62
REVERSELIGHTSWARNING=63

def Debug(text):
    if debugging:
        Domoticz.Log("DEBUG: "+str(text))

def Error(text):
    Domoticz.Log("ERROR: "+str(text))

def Info(text):
    if info or debugging:
        Domoticz.Log("INFO: "+str(text))

def LoginToVOC():
    global access_token,refresh_token,expirytimestamp

    Debug("LoginToVOC() called")
    
    try:
        response = requests.post(
            "https://volvoid.eu.volvocars.com/as/token.oauth2",
            headers = {
                'authorization': 'Basic aDRZZjBiOlU4WWtTYlZsNnh3c2c1WVFxWmZyZ1ZtSWFEcGhPc3kxUENhVXNpY1F0bzNUUjVrd2FKc2U0QVpkZ2ZJZmNMeXc=',
                'content-type': 'application/x-www-form-urlencoded',
                'user-agent': 'okhttp/4.10.0'
            },
            data = {
                'username': vocuser,
                'password': vocpass,
                'access_token_manager_id': 'JWTh4Yf0b',
                'grant_type': 'password',
                'scope': 'openid email profile care_by_volvo:financial_information:invoice:read care_by_volvo:financial_information:payment_method care_by_volvo:subscription:read customer:attributes customer:attributes:write order:attributes vehicle:attributes tsp_customer_api:all conve:brake_status conve:climatization_start_stop conve:command_accessibility conve:commands conve:diagnostics_engine_status conve:diagnostics_workshop conve:doors_status conve:engine_status conve:environment conve:fuel_status conve:honk_flash conve:lock conve:lock_status conve:navigation conve:odometer_status conve:trip_statistics conve:tyre_status conve:unlock conve:vehicle_relation conve:warnings conve:windows_status energy:battery_charge_level energy:charging_connection_status energy:charging_system_status energy:electric_range energy:estimated_charging_time energy:recharge_status vehicle:attributes'
            },
            timeout = TIMEOUT
        )
        if response.status_code!=200:
            Error("VolvoAPI failed calling https://volvoid.eu.volvocars.com/as/token.oauth2, HTTP Statuscode "+str(response.status_code))
            Error("Response: "+str(response.json()))
            access_token=None
            refresh_token=None
        else:
            Debug(response.content)
            try:
                resp=response.json()
                if resp==None or "error" in resp.keys():
                    Error("Login Failed, check your config, Response from Volvo: "+str(response.content))
                    refresh_token=None
                    access_token=None
                else:
                    Info("Login successful!")

                    #retrieve tokens
                    access_token = resp['access_token']
                    refresh_token = resp['refresh_token']
                    expirytimestamp=time.time()+resp['expires_in']

                    #after login: Get Vin
                    GetVin()
            except ValueError as exc:
                Error("Login Failed: unable to process json response from https://volvoid.eu.volvocars.com/as/token.oauth2 : "+str(exc))

    except Exception as error:
        Error("Login failed, check internet connection:")
        Error(error)

def RefreshVOCToken():
    global access_token,refresh_token,expirytimestamp

    Debug("RefreshToken() called")
    
    try:
        response = requests.post(
            "https://volvoid.eu.volvocars.com/as/token.oauth2",
            headers = {
                'authorization': 'Basic aDRZZjBiOlU4WWtTYlZsNnh3c2c1WVFxWmZyZ1ZtSWFEcGhPc3kxUENhVXNpY1F0bzNUUjVrd2FKc2U0QVpkZ2ZJZmNMeXc=',
                'content-type': 'application/x-www-form-urlencoded',
                'user-agent': 'okhttp/4.10.0'
            },
            data = {
                'access_token_manager_id': 'JWTh4Yf0b',
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }, 
            timeout=TIMEOUT
        )
        if response.status_code!=200:
            Error("VolvoAPI failed calling https://volvoid.eu.volvocars.com/as/token.oauth2, HTTP Statuscode "+str(response.status_code))
            access_token=None
            refresh_token=None
        else:
            Info("Refreshed token successful!")
            Debug("Volvo responded: "+str(response.json()))

            #retrieve tokens
            access_token = response.json()['access_token']
            refresh_token = response.json()['refresh_token']
            expirytimestamp=time.time()+response.json()['expires_in']

    except Exception as error:
        Error("Refresh failed:")
        Error(error)


def CheckRefreshToken():
    global lastloginattempttimestamp

    if refresh_token:
        if expirytimestamp-time.time()<60:  #if expires in 60 seconds: refresh
            RefreshVOCToken()
        else:
            Debug("Not refreshing token, expires in "+str(expirytimestamp-time.time())+" seconds")
    else:
        if time.time()-lastloginattempttimestamp>=MINTIMEBETWEENLOGINATTEMPTS:
            Debug("Nog logged in, attempting to login")
            lastloginattempttimestamp=time.time()
            LoginToVOC()
        else:
            Debug("Not logged in, retrying in "+str(MINTIMEBETWEENLOGINATTEMPTS-(time.time()-lastloginattempttimestamp))+" seconds")

def VolvoAPI(url,mediatype):
    Debug("VolvoAPI("+url+","+mediatype+") called")
    try:
        status = requests.get(
            url,
            headers= {
                "accept": mediatype,
                "vcc-api-key": vccapikey,
                "Authorization": "Bearer " + access_token
            },
            timeout=TIMEOUT
        )

        Debug("\nResult:")
        Debug(status)
        if status.status_code!=200:
            Error("VolvoAPI failed calling "+url+", HTTP Statuscode "+str(status.status_code))
            Error("Reponse: "+str(status.json()))
            return None
        else:
            sjson=status.json()
            sjson = json.dumps(status.json(), indent=4)
            Debug("\nResult JSON:")
            Debug(sjson)
            return status.json()

    except Exception as error:
        Error("VolvoAPI failed calling "+url+" with mediatype "+mediatype+" failed")
        Error(error)
        return None

def CheckVehicleDetails(vin):
    global batteryPackSize

    Debug("CheckVehicleDetails called")
    try:
        vehicle = VolvoAPI("https://api.volvocars.com/connected-vehicle/v2/vehicles/" + vin, "application/json")
        Info("Retrieved a " + str(vehicle["data"]["descriptions"]["model"]) + ", color " + str(
            vehicle["data"]["externalColour"]) + ", model year " + str(vehicle["data"]["modelYear"]))
        
        if vehicle:
            fuel_type = vehicle["data"]["fuelType"]
            
            if fuel_type == "ELECTRIC":
                Info("Setting BatteryCapacity to " + str(vehicle["data"]["batteryCapacityKWH"]))
                batteryPackSize = vehicle["data"]["batteryCapacityKWH"]
                
            elif fuel_type == "PETROL/ELECTRIC":
                Info("Vehicle is hybrid (PETROL/ELECTRIC).")
                # Additional handling for hybrid vehicles if needed
                
            elif fuel_type == "PETROL":
                Info("Vehicle runs on Petrol.")
                # Additional handling for petrol vehicles if needed
                
            elif fuel_type == "DIESEL":
                Info("Vehicle runs on Diesel.")
                # Additional handling for diesel vehicles if needed
                
            elif fuel_type == "NONE":
                Error("Selected VIN has no fuel type information.")
                # Additional handling for cases where fuel type is not specified
                
            else:
                Error("Selected VIN is not supported by this plugin due to unknown fuel type.")
                vin = None
                
    except Exception as error:
        Debug("CheckVehicleDetails failed:")
        Debug(error)
        vin = None

def GetVin():
    global vin

    Debug("GetVin called")
    try:
        vin=None
        vehicles = VolvoAPI("https://api.volvocars.com/connected-vehicle/v2/vehicles", "application/json")
        if vehicles:
            if (("data") in vehicles.keys()) and (len(vehicles["data"])>0):
                Info(str(len(vehicles["data"]))+" car(s) attached to your Volvo ID account: ")
                for x in vehicles["data"]:
                    Info("     "+x["vin"])
                if len(Parameters["Mode3"])==0:
                    vin = vehicles["data"][0]["vin"]
                    Info("No VIN in plugin config, selecting the 1st one ("+vin+") in your Volvo ID")
                else:
                    for x in vehicles["data"]:
                        if x["vin"]==Parameters["Mode3"]:
                            vin=Parameters["Mode3"]
                            Info("Using configured VIN "+str(vin))
                        else:
                            Debug("Ignoring VIN "+x["vin"])
                    if vin==None:
                        Error("manually configured VIN "+Parameters["Mode3"]+" does not exist in your Volvo id account, check your config")
            else:
                Error ("no cars configured for this volvo id")
                vin=None

            if vin:
                CheckVehicleDetails(vin)


    except Exception as error:
        Debug("Get vehicles failed:")
        Debug(error)
        vin=None


def UpdateSensor(vn, idx, name, tp, subtp, options, nv, sv):
    if (not vn in Devices) or (not idx in Devices[vn].Units):
        Domoticz.Unit(Name=Parameters["Name"]+"-"+name, Unit=idx, Type=tp, Subtype=subtp, DeviceID=vn, Options=options, Used=False).Create()
    Debug("Changing from " + str(Devices[vn].Units[idx].nValue) + "," + str(Devices[vn].Units[idx].sValue) + " to " + str(nv) + "," + str(sv))
    Devices[vn].Units[idx].nValue = int(nv)
    Devices[vn].Units[idx].sValue = sv
    Devices[vn].Units[idx].Update(Log=True)
    Domoticz.Log("General/Custom Sensor (" + Devices[vn].Units[idx].Name + ")")

def UpdateSelectorSwitch(vn, idx, name, options, nv, sv):
    if vn not in Devices or idx not in Devices[vn].Units:
        Domoticz.Unit(Name=Parameters["Name"] + "-" + name, Unit=idx, TypeName="Selector Switch", DeviceID=vn, Options=options, Used=False).Create()
    
    # Retrieve the device unit
    unit = Devices[vn].Units[idx]
    
    # Check if the current value and desired value are different
    if nv != unit.nValue or sv != unit.sValue:
        # Update the device unit values
        unit.nValue = nv
        unit.sValue = sv
        unit.Touch()
        Domoticz.Log("Selector Switch (" + unit.Name + ") updated")
    else:
        Debug("Not updating Selector Switch (" + unit.Name + ")")

def UpdateSwitch(vn, idx, name, nv, sv):
    Debug("UpdateSwitch(" + str(vn) + "," + str(idx) + "," + str(name) + "," + str(nv) + "," + str(sv) + " called")
    if (not vn in Devices) or (not idx in Devices[vn].Units):
        Domoticz.Unit(Name=Parameters["Name"] + "-" + name, Unit=idx, Type=244, Subtype=73, DeviceID=vn, Used=False).Create()
    Debug("Changing from " + str(Devices[vn].Units[idx].nValue) + "," + Devices[vn].Units[idx].sValue + " to " + str(nv) + "," + str(sv))
    Devices[vn].Units[idx].nValue = int(nv)
    Devices[vn].Units[idx].sValue = sv
    Devices[vn].Units[idx].Update(Log=True)
    Domoticz.Log("On/Off Switch (" + Devices[vn].Units[idx].Name + ")")

def UpdateSwitch(vn, idx, name, nv, sv):
    Debug("UpdateSwitch(" + str(vn) + "," + str(idx) + "," + str(name) + "," + str(nv) + "," + str(sv) + " called")
    if vn not in Devices or idx not in Devices[vn].Units:
        Domoticz.Unit(Name=Parameters["Name"] + "-" + name, Unit=idx, Type=113, Switchtype=3, DeviceID=vn, Used=False).Create()
    
    # Retrieve the device unit
    unit = Devices[vn].Units[idx]
    
    Debug("Changing from " + str(unit.nValue) + "," + unit.sValue + " to " + str(nv) + "," + str(sv))
    
    # Check if the current value and desired value are different
    if nv != unit.nValue or sv != unit.sValue:
        # Update the device unit values
        unit.Update(nValue=int(nv), sValue=sv)
        Domoticz.Log("RFXMeter Counter (" + unit.Name + ") updated to value: " + str(nv))
    else:
        Debug("Not updating RFXMeter Counter (" + unit.Name + ")")

def UpdateDoorOrWindow(vin, idx, name, value):
    Debug("UpdateDoorOrWindow(" + str(vin) + "," + str(idx) + "," + str(name) + "," + str(value) + ") called")
    if (not vin in Devices) or (not idx in Devices[vin].Units):
        Domoticz.Unit(Name=Parameters["Name"] + "-" + name, Unit=idx, Type=244, Subtype=73, Switchtype=11, DeviceID=vin, Used=False).Create()
    if value == "OPEN":
        Devices[vin].Units[idx].nValue = 1
        Devices[vin].Units[idx].sValue = "Open"
        Devices[vin].Units[idx].Update(Log=True)
        Domoticz.Log("Door/Window Contact (" + Devices[vin].Units[idx].Name + ")")
    elif value == "CLOSED":
        Devices[vin].Units[idx].nValue = 0
        Devices[vin].Units[idx].sValue = "Closed"
        Devices[vin].Units[idx].Update(Log=True)
        Domoticz.Log("Door/Window Contact (" + Devices[vin].Units[idx].Name + ")")
    else:
        Debug("Door/Windows status unchanged not updating " + Devices[vin].Units[idx].Name)

def UpdateLock(vin, idx, name, value):
    Debug("UpdateLock(" + str(vin) + "," + str(idx) + "," + str(name) + "," + str(value) + ") called")
    
    # Check if the device exists, if not, create it
    if (vin not in Devices) or (idx not in Devices[vin].Units):
        Debug("Creating device: " + Parameters["Name"] + "-" + name)
        Domoticz.Unit(Name=Parameters["Name"] + "-" + name, Unit=idx, Type=244, Subtype=73, Switchtype=19, DeviceID=vin, Used=False).Create()
    
    # Update the lock status
    if value == "LOCKED":
        nValue = 1
        sValue = "Locked"
    elif value == "UNLOCKED":
        nValue = 0
        sValue = "Unlocked"
    else:
        # Handle unexpected values
        Debug("Unexpected lock status value: " + value)
        return
    
    try:
        Debug("Before updating: nValue=" + str(Devices[vin].Units[idx].nValue) + ", sValue=" + Devices[vin].Units[idx].sValue)
        Devices[vin].Units[idx].Update(nValue=nValue, sValue=sValue, Log=True)
        Debug("After updating: nValue=" + str(Devices[vin].Units[idx].nValue) + ", sValue=" + Devices[vin].Units[idx].sValue)
        Domoticz.Log("Door Lock (" + Devices[vin].Units[idx].Name + ") updated")
    except Exception as e:
        Error("Failed to update lock status:")
        Error(str(e))

def UpdateOdoMeter(vn, idx, name, value):
    options = {'ValueQuantity': 'Custom', 'ValueUnits': 'km'}
    if vn not in Devices or idx not in Devices[vn].Units:
        Domoticz.Unit(Name=Parameters["Name"] + "-" + name, Unit=idx, Type=113, Switchtype=3, DeviceID=vin, Options=options, Used=False).Create()
    Debug("Changing from " + str(Devices[vn].Units[idx].nValue) + ", " + Devices[vn].Units[idx].sValue + " to " + str(value))
    Devices[vn].Units[idx].nValue = int(value)
    Devices[vn].Units[idx].sValue = str(value) + ";" + datetime.now().strftime("%Y-%m-%d")
    Devices[vn].Units[idx].Update(Log=True)
    Domoticz.Log("RFXMeter Counter (" + Devices[vn].Units[idx].Name + ") updated to value: " + str(value))

def GetOdoMeter():
    Debug("GetOdoMeter() Called")
    
    odometer = VolvoAPI("https://api.volvocars.com/connected-vehicle/v2/vehicles/"+vin+"/odometer","application/json")
    if odometer:
        Debug(json.dumps(odometer))
        value = int(odometer["data"]["odometer"]["value"])
        Debug("Retrieved odometer value: " + str(value))
        UpdateOdoMeter(vin, ODOMETER, "Odometer", value)
    else:
        Debug("Failed to retrieve odometer value")

def GetDoorWindowAndLockStatus():
    Debug("GetDoorAndLockStatus() Called")
    
    doors = VolvoAPI("https://api.volvocars.com/connected-vehicle/v2/vehicles/" + vin + "/doors", "application/json")
    if doors:
        Debug(json.dumps(doors))
        UpdateDoorOrWindow(vin, HOOD, "Hood", doors["data"]["hood"]["value"])
        UpdateDoorOrWindow(vin, TAILGATE, "Tailgate", doors["data"]["tailgate"]["value"])
        UpdateDoorOrWindow(vin, FRONTLEFTDOOR, "FrontLeftDoor", doors["data"]["frontLeftDoor"]["value"])
        UpdateDoorOrWindow(vin, FRONTRIGHTDOOR, "FrontRightDoor", doors["data"]["frontRightDoor"]["value"])
        UpdateDoorOrWindow(vin, REARLEFTDOOR, "RearLeftDoor", doors["data"]["rearLeftDoor"]["value"])
        UpdateDoorOrWindow(vin, REARRIGHTDOOR, "RearRightDoor", doors["data"]["rearRightDoor"]["value"])
        UpdateDoorOrWindow(vin, TANKLID, "TankLid", doors["data"]["tankLid"]["value"])
        UpdateLock(vin, CARLOCKED, "centralLock", doors["data"]["centralLock"]["value"])
    else:
        Error("Updating Doors failed")

    windows = VolvoAPI("https://api.volvocars.com/connected-vehicle/v2/vehicles/" + vin + "/windows", "application/json")
    if windows:
        Debug(json.dumps(windows))
        UpdateDoorOrWindow(vin, FRONTLEFTWINDOW, "FrontLeftWindow", windows["data"]["frontLeftWindow"]["value"])
        UpdateDoorOrWindow(vin, FRONTRIGHTWINDOW, "FrontRightWindow", windows["data"]["frontRightWindow"]["value"])
        UpdateDoorOrWindow(vin, REARLEFTWINDOW, "RearLeftWindow", windows["data"]["rearLeftWindow"]["value"])
        UpdateDoorOrWindow(vin, REARRIGHTWINDOW, "RearRightWindow", windows["data"]["rearRightWindow"]["value"])
        UpdateDoorOrWindow(vin, SUNROOF, "SunRoof", windows["data"]["sunroof"]["value"])
    else:
        Error("Updating Windows failed")

def UpdateTyrePressure(status,idx,name):
    #Calculate Charging Connect Status value
    newValue=0
    if status=="NO_WARNING":
        newValue=0
    elif status=="VERY_LOW_PRESSURE":
        newValue=10
    elif status=="LOW_PRESSURE":
        newValue=20
    elif status=="HIGH_PRESSURE":
        newValue=30
    elif status=="UNSPECIFIED":
        newValue=40
    else:
        Error("Unknown TyrePressureStatus")
        newValue=50

    #update selector switch for Charging Connection Status
    options = {"LevelActions": "|||",
              "LevelNames": "No Warning|VeryLow|Low|High|Unspecified|Unknown",
              "LevelOffHidden": "false",
              "SelectorStyle": "1"}
    UpdateSelectorSwitch(vin,idx,name,options,
                 int(newValue),
                 float(newValue))

def GetTyreStatus():
    Debug("GetTyreStatus() called")
    TyreStatus=VolvoAPI("https://api.volvocars.com/connected-vehicle/v2/vehicles/"+vin+"/tyres","application/json")
    if TyreStatus:
        Debug(json.dumps(TyreStatus))
        UpdateTyrePressure(TyreStatus["data"]["frontRight"]["value"],FRONTRIGHTTYREPRESSURE,"FrontRightTyrePressure")
        UpdateTyrePressure(TyreStatus["data"]["frontLeft"]["value"],FRONTLEFTTYREPRESSURE,"FrontLeftTyrePressure")
        UpdateTyrePressure(TyreStatus["data"]["rearRight"]["value"],REARRIGHTTYREPRESSURE,"RearRightTyrePressure")
        UpdateTyrePressure(TyreStatus["data"]["rearLeft"]["value"],REARLEFTTYREPRESSURE,"RearLeftTyrePressure")
    else:
        Error("Updating Tyre Status failed")

def UpdateWarning(status,idx,name):
    #Calculate Charging Connect Status value
    newValue=0
    if status=="NO_WARNING":
        newValue=0
    elif status=="FAILURE":
        newValue=10
    elif status=="UNSPECIFIED":
        newValue=20
    else:
        Error("Unknown Warning Value")
        newValue=30

    #update selector switch for Charging Connection Status
    options = {"LevelActions": "|||",
              "LevelNames": "No Warning|Failure|Unspecified|Unknown",
              "LevelOffHidden": "false",
              "SelectorStyle": "1"}
    UpdateSelectorSwitch(vin,idx,name,options,
                 int(newValue),
                 float(newValue))

def GetWarnings():
    Debug("GetWarningStatus() called")
    WarningStatus=VolvoAPI("https://api.volvocars.com/connected-vehicle/v2/vehicles/"+vin+"/warnings","application/json")
    if WarningStatus:
        Debug(json.dumps(WarningStatus))
        UpdateWarning(WarningStatus["data"]["brakeLightCenterWarning"]["value"],BRAKELIGHTCENTERWARNING,"BrakeLightCenterWarning")
        UpdateWarning(WarningStatus["data"]["brakeLightLeftWarning"]["value"],BRAKELIGHTLEFTWARNING,"BrakeLightLeftWarning")
        UpdateWarning(WarningStatus["data"]["brakeLightRightWarning"]["value"],BRAKELIGHTRIGHTWARNING,"BrakeLightRightWarning")
        UpdateWarning(WarningStatus["data"]["fogLightFrontWarning"]["value"],FOGLIGHTFRONTWARNING,"fogLightFrontWarning")
        UpdateWarning(WarningStatus["data"]["fogLightRearWarning"]["value"],FOGLIGHTREARWARNING,"fogLightRearWarning")
        UpdateWarning(WarningStatus["data"]["positionLightFrontLeftWarning"]["value"],POSITIONLIGHTFRONTLEFTWARNING,"positionLightFrontLeftWarning")
        UpdateWarning(WarningStatus["data"]["positionLightFrontRightWarning"]["value"],POSITIONLIGHTFRONTRIGHTWARNING,"positionLightFrontRightWarning")
        UpdateWarning(WarningStatus["data"]["positionLightRearLeftWarning"]["value"],POSITIONLIGHTREARLEFTWARNING,"positionLightRearLeftWarning")
        UpdateWarning(WarningStatus["data"]["positionLightRearRightWarning"]["value"],POSITIONLIGHTREARRIGHTWARNING,"positionLightRearRightWarning")
        UpdateWarning(WarningStatus["data"]["highBeamLeftWarning"]["value"],HIGHBEAMLEFTWARNING,"highBeamLeftWarning")
        UpdateWarning(WarningStatus["data"]["highBeamRightWarning"]["value"],HIGHBEAMRIGHTWARNING,"highBeamRightWarning")
        UpdateWarning(WarningStatus["data"]["lowBeamLeftWarning"]["value"],LOWBEAMLEFTWARNING,"lowBeamLeftWarning")
        UpdateWarning(WarningStatus["data"]["lowBeamRightWarning"]["value"],LOWBEAMRIGHTWARNING,"lowBeamRightWarning")
        UpdateWarning(WarningStatus["data"]["daytimeRunningLightLeftWarning"]["value"],DAYTIMERUNNINGLIGHTLEFTWARNING,"daytimeRunningLightLeftWarning")
        UpdateWarning(WarningStatus["data"]["daytimeRunningLightRightWarning"]["value"],DAYTIMERUNNINGLIGHTRIGHTWARNING,"daytimeRunningLightRightWarning")
        UpdateWarning(WarningStatus["data"]["turnIndicationFrontLeftWarning"]["value"],TURNINDICATIONFRONTLEFTWARNING,"turnIndicationFrontLeftWarning")
        UpdateWarning(WarningStatus["data"]["turnIndicationFrontRightWarning"]["value"],TURNINDICATIONFRONTRIGHTWARNING,"turnIndicationFrontRightWarning")
        UpdateWarning(WarningStatus["data"]["turnIndicationRearLeftWarning"]["value"],TURNINDICATIONREARLEFTWARNING,"turnIndicationRearLeftWarning")
        UpdateWarning(WarningStatus["data"]["turnIndicationRearRightWarning"]["value"],TURNINDICATIONREARRIGHTWARNING,"turnIndicationRearRightWarning")
        UpdateWarning(WarningStatus["data"]["registrationPlateLightWarning"]["value"],REGISTRATIONPLATELIGHTWARNING,"registrationPlateLightWarning")
        UpdateWarning(WarningStatus["data"]["sideMarkLightsWarning"]["value"],SIDEMARKLIGHTSWARNING,"sideMarkLightsWarning")
        UpdateWarning(WarningStatus["data"]["hazardLightsWarning"]["value"],HAZARDLIGHTSWARNING,"hazardMarkLightsWarning")
        UpdateWarning(WarningStatus["data"]["reverseLightsWarning"]["value"],REVERSELIGHTSWARNING,"reverseMarkLightsWarning")
    else:
        Error("Updating Tyre Status failed")

def UpdateLevel(status,idx,name):
    #Calculate Charging Connect Status value
    newValue=0
    if status=="NO_WARNING":
        newValue=0
    elif status=="TOO_LOW":
        newValue=10
    elif status=="TOO_HIGH":
        newValue=20
    elif status=="SERVICE_REQUIRED":
        newValue=30
    elif status=="UNSPECIFIED":
        newValue=40
    else:
        Error("Uwknown Oil or Coolantlevel status")
        newValue=50

    #update selector switch for Charging Connection Status
    options = {"LevelActions": "|||",
              "LevelNames": "No Warning|Too Low|Too High|Service Required|Unspecified|Unknown",
              "LevelOffHidden": "false",
              "SelectorStyle": "1"}
    UpdateSelectorSwitch(vin,idx,name,options,
                 int(newValue),
                 float(newValue))

def GetEngineStatus():
    Debug("GetEngineStatus() called")
    EngineStatus=VolvoAPI("https://api.volvocars.com/connected-vehicle/v2/vehicles/"+vin+"/engine-status","application/json")
    if EngineStatus:
        Debug(json.dumps(EngineStatus))
        if EngineStatus["data"]["engineStatus"]["value"]=="STOPPED":
            UpdateSwitch(vin,ENGINERUNNING,"engineStatus",0,"Off")
        else:
            UpdateSwitch(vin,ENGINERUNNING,"engineStatus",1,"On")
    else:
        Error("Updating Engine Status failed")

def GetEngine():
    Debug("GetEngine() called")
    EngineStatus=VolvoAPI("https://api.volvocars.com/connected-vehicle/v2/vehicles/"+vin+"/engine","application/json")
    if EngineStatus:
        Debug(json.dumps(EngineStatus))
        UpdateLevel(EngineStatus["data"]["engineCoolantLevelWarning"]["value"],ENGINECOOLANTLEVEL,"engineCoolantLevel")
        UpdateLevel(EngineStatus["data"]["oilLevelWarning"]["value"],OILLEVEL,"oilLevel")
    else:
        Error("Updating Engine failed")

def GetDiagnostics():
    Debug("GetDiagnostics() called")
    Diagnostics=VolvoAPI("https://api.volvocars.com/connected-vehicle/v2/vehicles/"+vin+"/diagnostics","application/json")
    if Diagnostics:
        Debug(json.dumps(Diagnostics))
        
        #update engineHoursToService
        UpdateSensor(vin,ENGINEHOURSTOSERVICE,"EngineHoursToService",243,31,{'Custom':'1;hrs'},
                     int(Diagnostics["data"]["engineHoursToService"]["value"]),
                     float(Diagnostics["data"]["engineHoursToService"]["value"]))

        #update kmToService
        UpdateSensor(vin,KMTOSERVICE,"KmToService",243,31,{'Custom':'1;km'},
                     int(Diagnostics["data"]["distanceToService"]["value"]),
                     float(Diagnostics["data"]["distanceToService"]["value"]))

        #update monthsToService
        UpdateSensor(vin,MONTHSTOSERVICE,"MonthsToService",243,31,{'Custom':'1;months'},
                     int(Diagnostics["data"]["timeToService"]["value"]),
                     float(Diagnostics["data"]["timeToService"]["value"]))

        #update selector switch for ServiceStatus
        options = {"LevelActions": "|||",
                  "LevelNames": "No Warning|Regular Maintenance Almost|Engine Hours Almost|Distance Driven Almost|Regular Maintenance|Engine Hours|Distance Driven|Regular Maintenance Overdue|Engine Hours Overdue|Distance Driven Overdue|Unknown",
                  "LevelOffHidden": "false",
                  "SelectorStyle": "1"}
        status=Diagnostics["data"]["serviceWarning"]["value"]
        newValue=0
        if status=="NO_WARNING":
            newValue=0
        elif status=="REGULAR_MAINTENANCE_ALMOST_TIME_FOR_SERVICE":
            newValue=10
        elif status=="REGULAR_MAINTENANCE_ALMOST_TIME_FOR_SERVICE":
            newValue=20
        elif status=="DISTANCE_DRIVEN_ALMOST_TIME_FOR_SERVICE":
            newValue=30
        elif status=="REGULAR_MAINTENANCE_TIME_FOR_SERVICE":
            newValue=40
        elif status=="REGULAR_MAINTENANCE_TIME_FOR_SERVICE":
            newValue=50
        elif status=="DISTANCE_DRIVEN_TIME_FOR_SERVICE":
            newValue=60
        elif status=="REGULAR_MAINTENANCE_OVERDUE_FOR_SERVICE":
            newValue=70
        elif status=="REGULAR_MAINTENANCE_OVERDUE_FOR_SERVICE":
            newValue=80
        elif status=="DISTANCE_DRIVEN_OVERDUE_FOR_SERVICE":
            newValue=90
        else:
            newValue=100
        UpdateSelectorSwitch(vin,SERVICESTATUS,"ServiceStatus",options, int(newValue), float(newValue)) 
        
        #update selector switch for Washerfluidlevel
        UpdateLevel(Diagnostics["data"]["washerFluidLevelWarning"]["value"],WASHERFLUIDLEVEL,"WasherFluidLevel")
    else:
        Error("Updating Diagnostics failed")

def GetRechargeStatus():
    global batteryPackSize

    Debug("GetRechargeStatus() called")
    try:
        vehicle = VolvoAPI("https://api.volvocars.com/connected-vehicle/v2/vehicles/" + vin, "application/json")
        if vehicle and vehicle["data"]["fuelType"] == "ELECTRIC":
            RechargeStatus = VolvoAPI("https://api.volvocars.com/energy/v1/vehicles/" + vin + "/recharge-status",
                                      "application/vnd.volvocars.api.energy.vehicledata.v1+json")
            if RechargeStatus:
                Debug(json.dumps(RechargeStatus))

                # update Remaining Range Device
                UpdateSensor(vin, REMAININGRANGE, "electricRange", 243, 31, {'Custom': '1;km'},
                             int(RechargeStatus["data"]["electricRange"]["value"]),
                             float(RechargeStatus["data"]["electricRange"]["value"]))

                # update Percentage Device
                UpdateSensor(vin, BATTERYCHARGELEVEL, "batteryChargeLevel", 243, 6, None,
                             float(RechargeStatus["data"]["batteryChargeLevel"]["value"]),
                             float(RechargeStatus["data"]["batteryChargeLevel"]["value"]))

                # update Fullrange Device
                CalculatedRange = float(RechargeStatus["data"]["electricRange"]["value"]) * 100 / float(
                    RechargeStatus["data"]["batteryChargeLevel"]["value"])
                UpdateSensor(vin, FULLRANGE, "fullRange", 243, 31, {'Custom': '1;km'},
                             int(CalculatedRange),
                             "{:.1f}".format(CalculatedRange))

                # update EstimatedEfficiency Device
                estimatedEfficiency = (batteryPackSize * float(
                    RechargeStatus["data"]["batteryChargeLevel"]["value"])) / float(
                    RechargeStatus["data"]["electricRange"]["value"])
                UpdateSensor(vin, ESTIMATEDEFFICIENCY, "estimatedEfficiency", 243, 31, {'Custom': '1;kWh/100km'},
                             int(estimatedEfficiency),
                             "{:.1f}".format(estimatedEfficiency))

                # update Remaining ChargingTime Device
                UpdateSensor(vin, ESTIMATEDCHARGINGTIME, "estimatedChargingTime", 243, 31, {'Custom': '1;min'},
                             int(RechargeStatus["data"]["estimatedChargingTime"]["value"]),
                             float(RechargeStatus["data"]["estimatedChargingTime"]["value"]))

                # Calculate Charging Connect Status value
                connstatus = RechargeStatus["data"]["chargingConnectionStatus"]["value"]
                newValue = 0
                if connstatus == "CONNECTION_STATUS_DISCONNECTED":
                    newValue = 0
                elif connstatus == "CONNECTION_STATUS_CONNECTED_AC":
                    newValue = 10
                elif connstatus == "CONNECTION_STATUS_CONNECTED_DC":
                    newValue = 20
                elif connstatus == "CONNECTION_STATUS_UNSPECIFIED":
                    newValue = 30
                else:
                    newValue = 30

                # update selector switch for Charging Connection Status
                options = {"LevelActions": "|||",
                           "LevelNames": "Disconnected|ACConnected|DCConnected|Unspecified",
                           "LevelOffHidden": "false",
                           "SelectorStyle": "1"}
                UpdateSelectorSwitch(vin, CHARGINGCONNECTIONSTATUS, "chargingConnectionStatus", options,
                                     int(newValue),
                                     float(newValue))

                # Calculate Charging system Status value
                chargestatus = RechargeStatus["data"]["chargingSystemStatus"]["value"]
                newValue = 0
                if chargestatus == "CHARGING_SYSTEM_IDLE":
                    newValue = 0
                elif chargestatus == "CHARGING_SYSTEM_CHARGING":
                    newValue = 10
                elif chargestatus == "CHARGING_SYSTEM_FAULT":
                    newValue = 20
                elif chargestatus == "CHARGING_SYSTEM_UNSPECIFIED":
                    newValue = 30
                else:
                    newValue = 30

                # update selector switch for Charging Connection Status
                options = {"LevelActions": "|||",
                           "LevelNames": "Idle|Charging|Fault|Unspecified",
                           "LevelOffHidden": "false",
                           "SelectorStyle": "1"}
                UpdateSelectorSwitch(vin, CHARGINGSYSTEMSTATUS, "chargingSystemStatus", options, int(newValue),
                                     float(newValue))
        else:
            Info("Vehicle is not electric, RechargeStatus not updated.")
    except Exception as e:
        Error("Exception occurred during updating Recharge Status: {}".format(str(e)))

def GetLocation():
    def DistanceBetweenCoords(coords1, coords2):
        # Approximate radius of earth in km
        R = 6373.0

        lat1 = radians(float(coords1[0]))
        lon1 = radians(float(coords1[1]))
        lat2 = radians(float(coords2[0]))
        lon2 = radians(float(coords2[1]))

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c

        Debug("Result: " + str(distance))
        return distance

    Debug("GetLocation() called")
    Location = VolvoAPI("https://api.volvocars.com/location/v1/vehicles/" + vin + "/location", "application/json")
    if Location:
        Debug(json.dumps(Location))
        Debug("Location is " + str(Location["data"]["geometry"]["coordinates"][0]))
        UpdateSensor(vin, LONGITUDE, "Longitude", 243, 31, {'Custom': '1;lon'},
                     int(Location["data"]["geometry"]["coordinates"][0]),
                     Location["data"]["geometry"]["coordinates"][0])
        UpdateSensor(vin, LATTITUDE, "Lattitude", 243, 31, {'Custom': '1;lat'},
                     int(Location["data"]["geometry"]["coordinates"][1]),
                     Location["data"]["geometry"]["coordinates"][1])
        UpdateSensor(vin, ALTITUDE, "Altitude", 243, 31, {'Custom': '1;alt'},
                     int(Location["data"]["geometry"]["coordinates"][2]),
                     Location["data"]["geometry"]["coordinates"][2])
        UpdateSensor(vin, HEADING, "Heading", 243, 31, {'Custom': '1;degrees'},
                     int(Location["data"]["properties"]["heading"]),
                     str(Location["data"]["properties"]["heading"]))
        if len(Settings["Location"]) > 0:
            Debug("Domoticz location is " + Settings["Location"])
            DomoticzLocation = Settings["Location"].split(";")
            if len(DomoticzLocation) == 2:
                VolvoLocation = (Location["data"]["geometry"]["coordinates"][1],
                                 Location["data"]["geometry"]["coordinates"][0])
                Distance2Home = DistanceBetweenCoords(DomoticzLocation, VolvoLocation)
                Debug("Distance to volvo is " + str(Distance2Home))
                UpdateSensor(vin, DISTANCE2HOME, "Distance2Home", 243, 31, {'Custom': '1;km'}, int(Distance2Home),
                             str(Distance2Home))
            else:
                Debug("Invalid location entered in domoticz config")
        else:
            Debug("No location entered in domoticz config")
    else:
        Error("GetLocation failed")



def UpdateABRP():
    try:
        #get params

        #utc
        dt = datetime.datetime.now(timezone.utc)
        utc_time = dt.replace(tzinfo=timezone.utc)
        utc_timestamp = utc_time.timestamp()

        #chargelevel
        chargelevel=Devices[vin].Units[BATTERYCHARGELEVEL].nValue
        
        #check if we are charging (dnd if so whiuch type)
        is_charging=0
        is_dcfc=0
        if Devices[vin].Units[CHARGINGSYSTEMSTATUS].nValue==10:
            if Devices[vin].Units[CHARGINGCONNECTIONSTATUS].nValue==10:
                is_charging=1
            elif Devices[vin].Units[CHARGINGCONNECTIONSTATUS].nValue==20:
                is_charging=1
                is_dcfc=1

        #odometer
        odometer=Devices[vin].Units[ODOMETER].nValue;

        #Remaining
        RemainingRange=Devices[vin].Units[REMAININGRANGE].nValue;

        #make the call
        url='http://api.iternio.com/1/tlm/send?api_key='+abrp_api_key+'&token='+abrp_token+'&tlm={"utc":'+str(utc_timestamp)+',"soc":'+str(chargelevel)+',"is_charging":'+str(is_charging)+',"is_dcfc":'+str(is_dcfc)+',"est_battery_range":'+str(RemainingRange)+',"odometer":'+str(odometer)+'}'
        Debug("ABRP url = "+url)
        response=requests.get(url,timeout=TIMEOUT)
        Debug(response.text)
        if response.status_code==200 and response.json()["status"]=="ok":
            Debug("ABRP call succeeded")
        else:
            Error("ABRP call failed")

    except Exception as error:
        Error("Error updating ABRP SOC")
        Error(error)


def Heartbeat():
    global lastupdate

    Debug("Heartbeat() called")
    CheckRefreshToken()

    if vin:
        #handle climatization logic
        if (not vin in Devices) or (not CLIMATIZATION in Devices[vin].Units):
            #no Climate device, let's create
            UpdateSwitch(vin,CLIMATIZATION,"Climatization",0,"Off")
        else:
            Debug("Already exists")

        if Devices[vin].Units[CLIMATIZATION].nValue==1:
            if time.time()>climatizationstoptimestamp:
                Info("Switch off climatization, timer expired")
                UpdateSwitch(vin,CLIMATIZATION,"Climatization",0,"Off")
            else:
                Debug("Climatization on, will stop in "+str(climatizationstoptimestamp-time.time())+" seconds")
        else:
            Debug("Climatization switched off, do nothing")


        #handle updates
        if time.time()-lastupdate>=updateinterval:
            # do updates
            Info("Updating Devices")
            lastupdate=time.time()
            GetRechargeStatus()
            GetDoorWindowAndLockStatus()
            GetOdoMeter()
            GetTyreStatus()
            GetDiagnostics()
            GetLocation()
            GetEngineStatus() 
            GetEngine()
            GetWarnings()
        else:
            Debug("Not updating, "+str(updateinterval-(time.time()-lastupdate))+" to update")
        
        #update ABRP SOC
        if abrp_api_key and abrp_token:
            #Check if synmc device exists.
            if (not vin in Devices) or (not ABRPSYNC in Devices[vin].Units):
                UpdateSwitch(vin,ABRPSYNC,"Connect to ABRP",1,"On")

            #Check if we have to sync
            if Devices[vin].Units[ABRPSYNC].nValue==1:
                UpdateABRP()
            else:
                Debug("ABRPSyncing switched off")
        else:
            Debug("No ABRP token and/or apikey, ignoring")

    else:
        Debug("No vin, do nothing")

def HandleClimatizationCommand(vin, idx, command):
    global climatizationstoptimestamp, climatizationoperationid

    if refresh_token:
        url = "https://api.volvocars.com/connected-vehicle/v2/vehicles/" + vin + '/commands/climatization-start'
        climatizationstoptimestamp = time.time() + 30 * 60  # make sure we switch off after 30 mins
        nv = 1

        if command == 'Off':
            url = "https://api.volvocars.com/connected-vehicle/v2/vehicles/" + vin + '/commands/climatization-stop'
            nv = 0

        try:
            Debug("URL: {}".format(url))
            status = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "vcc-api-key": vccapikey,
                    "Authorization": "Bearer " + access_token
                },
                timeout=TIMEOUT
            )

            Debug("\nResult:")
            Debug(status)

            sjson = json.dumps(status.json(), indent=4)
            Debug("\nResult JSON:")
            Debug(sjson)
            if status.status_code == 200:
                if status.json()["data"]["invokeStatus"] == "COMPLETED":
                    UpdateSwitch(vin, CLIMATIZATION, "Climatization", nv, command)
                else:
                    Error("Climatization did not start/stop, API returned code " + status.json()["data"][
                        "invokeStatus"])
            else:
                Error("Climatization did not start/stop, webserver returned " + str(status.status_code) + ", result: " + sjson)

        except Exception as err:
            Error("Handle climatization command failed:")
            Error(err)

def HandleLockCommand(vin,idx,command):
    global climatizationstoptimestamp,climatizationoperationid

    if refresh_token:
        url = "https://api.volvocars.com/connected-vehicle/v2/vehicles/" + vin + '/commands/lock'
        cmd = "LOCKED"
        
        if command=='Off':
            url = "https://api.volvocars.com/connected-vehicle/v2/vehicles/" + vin + '/commands/unlock'
            cmd = "UNLOCKED"

        try:
            Debug("URL: {}".format(url))
            status = requests.post(
                url,
                headers= {
                    "Content-Type": "application/json",
                    "vcc-api-key": vccapikey,
                    "Authorization": "Bearer " + access_token
                },
                timeout=TIMEOUT
            )

            Debug("\nResult:")
            Debug(status)
            sjson = json.dumps(status.json(), indent=4)
            Debug("\nResult JSON:")
            Debug(sjson)
            if status.status_code==200:
                if (status.json()["data"]["invokeStatus"]=="COMPLETED"):
                    UpdateLock(vin,CARLOCKED,"CarLocked",cmd)
                else:
                    Error("Car did not lock/unlock, API returned code "+status.json()["data"]["invokeStatus"])
            else:
                Error("car did not lock/unlock, webserver returned "+str(status.status_code)+", result: "+sjson)

        except Exception as error:
            Error("lock/unlock command failed:")
            Error(error)

class BasePlugin:
    enabled = False
    def __init__(self):
        #self.var = 123
        return

    def onStart(self):
        global vocuser,vocpass,vccapikey,debugging,info,lastupdate,updateinterval,expirytimestamp,abrp_api_key,abrp_token
        Debug("OnStart called")
        
        #read params
        if Parameters["Mode6"] in {"-1","126"}:
            Domoticz.Debugging(int(Parameters["Mode6"]))
            debugging=True
            info=True
        elif Parameters["Mode6"] in {"62"}:
            Domoticz.Debugging(int(Parameters["Mode6"]))
            info=True
            debugging=False
        else:
            debugging=False
            info=True

        if debugging:
            DumpConfigToLog()

        #initiate vars
        values=Parameters["Mode5"].split(":")
        if len(values)==2:
            Debug("We have a valid ABRP config")
            abrp_api_key=values[0]
            abrp_token=values[1]
            Debug("ABRP api key="+abrp_api_key+", token="+abrp_token)
        else:
            Debug("len="+str(len(values)))

        vocuser=Parameters["Username"]
        vocpass=Parameters["Password"]
        vccapikey=Parameters["Mode1"]
        updateinterval=int(Parameters["Mode2"])
        if (updateinterval<90):
            Info("Updateinterval too low, correcting to 90 secs")
            updateinterval=89 # putting is too exact 80 might sometimes lead to update after 100 secs 
        lastupdate=time.time()-updateinterval-1 #force update
        expirytimestamp=time.time()-1 #force update


        #1st pass
        Heartbeat()

    def onStop(self):
        Debug("onStop called")

    def onConnect(self, Connection, Status, Description):
        Debug("onConnect called")

    def onMessage(self, Connection, Data):
        Debug("onMessage called")

    def onCommand(self, DeviceID, Unit, Command, Level, Color):
        Debug("onCommand called for Device " + str(DeviceID) + " Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

        if Unit==CLIMATIZATION:
            Debug("Handle climatization")
            HandleClimatizationCommand(DeviceID,Unit,Command)
        elif Unit==CARLOCKED:
            Debug("Handle CarLock")
            HandleLockCommand(DeviceID,Unit,Command)
        elif Unit==ABRPSYNC:
            if Command=='On':
                UpdateSwitch(vin,ABRPSYNC,"ABRPSYNC",1,Command)
            else:
                UpdateSwitch(vin,ABRPSYNC,"ABRPSYNC",0,Command)
        else:
            Debug("uknown command")

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Debug("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Debug("onDisconnect called")

    def onHeartbeat(self):
        Debug("onHeartbeat called")
        Heartbeat()

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(DeviceID, Unit, Command, Level, Color):
    global _plugin
    _plugin.onCommand(DeviceID, Unit, Command, Level, Color)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Debug("Device count: " + str(len(Devices)))
    for DeviceName in Devices:
        Device = Devices[DeviceName]
        Debug("Device ID:       '" + str(Device.DeviceID) + "'")
        Debug("--->Unit Count:      '" + str(len(Device.Units)) + "'")
        for UnitNo in Device.Units:
            Unit = Device.Units[UnitNo]
            Debug("--->Unit:           " + str(UnitNo))
            Debug("--->Unit Name:     '" + Unit.Name + "'")
            Debug("--->Unit nValue:    " + str(Unit.nValue))
            Debug("--->Unit sValue:   '" + Unit.sValue + "'")
            Debug("--->Unit LastLevel: " + str(Unit.LastLevel))
    return