import http.client
import json
from dotenv import load_dotenv
import os
import streamlit as st
from geopy.geocoders import Nominatim
import pandas as pd
from serpapi import GoogleSearch
from boto.s3.connection import S3Connection


#Loading .env file
def configure():
    load_dotenv()


#Bringing data from met API
def getweather(lat, long):
    configure()
    conn = http.client.HTTPSConnection("api-metoffice.apiconnect.ibmcloud.com")

    headers = {
        'X-IBM-Client-Id': st.secrets['api_key'], #Replace os.getenv('api_key') with your API Key. Or use a .env file containing the creds
        'X-IBM-Client-Secret': st.secrets['api_secret'], #Replace os.getenv('api_secret') with your API Secret
        'accept': "application/json"
        }

    conn.request("GET", f"/v0/forecasts/point/three-hourly?excludeParameterMetadata=true&includeLocationName=true&latitude={lat}&longitude={long}", headers=headers)

    res = conn.getresponse()
    data = res.read()
    js = json.loads(data) #Return data as JSON

    #return(data.decode("utf-8")) Uncomment this for original data return
    return js



st.title("Weather Dashboard")

# Sidebar
st.sidebar.markdown("""Pulling Info from Met Office Weather Datahub service  
                    https://www.metoffice.gov.uk/services/data/met-office-weather-datahub  
                    And Google Search data using SerpApi     
                    https://serpapi.com
""")
check = st.sidebar.checkbox("Use Custom Latitude/Longitude")

#Initialising Nominatim
geolocator = Nominatim(user_agent="Streamlit")

if not check:    
    placechoice = st.text_input("Enter Location", key="keytext", value="London")

    mylocation = geolocator.geocode(placechoice) # Using Nominatim to get lat/long coords from Location
    choice1 = mylocation.latitude
    choice2 = mylocation.longitude

if check:
    choice1 = st.number_input('Latitude', min_value = -85, max_value = 85, key="keylat")
    choice2 = st.number_input('Longitude', min_value = -180, max_value = 179, key="keylong")
    
# Narrowing down JSON
data = getweather(choice1, choice2)
location = data["features"][0]["properties"]["location"]["name"]
timeSeries0 = data["features"][0]["properties"]["timeSeries"][0]
alltimeseries = data["features"][0]["properties"]["timeSeries"]

tdate = alltimeseries[1]["time"][:10]
#24 Hour Temperature graph

def graphtemp():
    date = []
    temp = []
    for v in alltimeseries[1:10]:
        date.append(v["time"][:-1])
        temp.append(v["feelsLikeTemp"])    
    df = pd.DataFrame({"Temperature  °C" : temp}, index=date)
    df.index = pd.to_datetime(df.index)
    return df

# Metrics Title  

col1,col2,col3 = st.columns(3)
with col2:
    st.title(location)
    st.caption(f"Lat: {choice1}, Long: {choice2}")
with st.expander(f"24 Hour Temperature Chart - {tdate}"):
    st.line_chart(graphtemp())
st.header(f"48 Hour Forecast")

# Formatting page to display metrics

col1, col2, col3, col4, col5 = st.columns([2,2,3,3,2])

days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def get48hrforecast():
    
    # Grab Images using SerpAPI
    configure()
    params = {
    "engine": "google",
    "q": f"{location} weather",
    "location": "United Kingdom",
    "gl": "uk",
    "api_key": st.secrets['serpkey']
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    if "answer_box" in results:
        ansbox = results["answer_box"]
    else:
        ansbox = None

    #Start Building Metrics Table
    tdate = timeSeries0["time"][:10]
    dof = pd.Timestamp(tdate)
    temp1, temp2, temp3 = timeSeries0["feelsLikeTemp"], timeSeries0["windSpeed10m"], timeSeries0["probOfRain"]
    if ansbox is not None: # If google has a forecast image for location
        col1.image(ansbox["thumbnail"], width=91)
    col2.metric(days[dof.dayofweek], timeSeries0["time"][11:-1])
    col3.metric("Temperature", f'{temp1} °C')
    col4.metric("Windspeed", f'{temp2} mph')
    col5.metric("Rain Probability", f'{temp3}%')
    curday = days[dof.dayofweek]
    foreday = 0
    for v in alltimeseries[1:16]:
        tm, t, w, r = v["time"], v["feelsLikeTemp"], v["windSpeed10m"], v["probOfRain"]
        tdate = v["time"][:10]
        dof = pd.Timestamp(tdate)
        if ansbox: 
            if days[dof.dayofweek] == curday: # If still on todays date show todays forecast image
                col1.image(ansbox["forecast"][foreday]["thumbnail"], width=91)
            else: # If date does not match todays date, move to next forecast image
                curday = days[dof.dayofweek]
                foreday += 1
                col1.image(ansbox["forecast"][foreday]["thumbnail"], width=91)
        
        col2.metric(days[dof.dayofweek], tm[11:-1], tm[:10], delta_color="off")
        col3.metric("Temperature", f'{t} °C', f"{round(t - temp1, 2)} °C" )
        col4.metric("Windspeed", f'{w} mph', f"{round(w - temp2, 2)} mph")
        col5.metric("Rain Probability", f'{r}%', f"{round(r - temp3, 2)} %")
        temp1, temp2, temp3 = t, w, r

        
get48hrforecast()