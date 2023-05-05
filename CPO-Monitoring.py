import json
import requests
import pandas as pd
import geopandas as gpd
import fiona
#import leafmap
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
#%matplotlib inline
#%config InlineBackend.figure_format='retina'

# Geometrie Schweiz
url_schweiz = "geodata/swissBOUNDARIES3D_1_4_TLM_LANDESGEBIET_WGS84.shp"
Schweiz = gpd.read_file(url_schweiz)
Schweiz = Schweiz.loc[Schweiz.NAME=="Schweiz"]
Schweiz = Schweiz.set_crs('epsg:4326')

# Daten ich-tanke-strom
url = "https://data.geo.admin.ch/ch.bfe.ladestellen-elektromobilitaet/data/oicp/ch.bfe.ladestellen-elektromobilitaet.json"
r = requests.get(url)
data = r.json()
df = pd.json_normalize(data["EVSEData"], record_path=['EVSEDataRecord'], meta=['OperatorID'])
# nur Schweiz
df = df[df["Address.Country"] == "CHE"]

# new data frame with split value columns
new = df["GeoCoordinates.Google"].str.split(" ", n = 1, expand = True)
 
# making separate first name column from new data frame
df["lat"] = new[1]
df["lat"] = df["lat"].astype(float)
 
# making separate last name column from new data frame
df["lon"]= new[0]
df["lon"] = df["lon"].astype(float)

df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lat,df.lon))
df = df.set_crs('epsg:4326')

# spatial join
df_join = gpd.sjoin(Schweiz, df, how='right', predicate='intersects')
df = df_join[df_join["UUID"].notnull()]

#Ladesaeulen
df_ladesaeulen = df['OperatorID'].value_counts().to_frame().reset_index()
df_ladesaeulen.rename(columns={"count": "Ladesaeulen"}, inplace=True)
df_ladesaeulen.rename(columns={"index": "OperatorID"}, inplace=True)

#Standorte
df_standorte = df[["GeoCoordinates.Google","OperatorID"]]
df_standorte = df_standorte.groupby('OperatorID')['GeoCoordinates.Google'].apply(lambda x: len(np.unique(x))).to_frame().reset_index()
df_standorte.rename(columns={"GeoCoordinates.Google": "Standorte"}, inplace=True)

#Plugs
df = pd.json_normalize(data["EVSEData"], record_path=['EVSEDataRecord', 'Plugs'], meta=['OperatorID', ['EVSEDataRecord', 'Address', 'Country'], ['EVSEDataRecord', 'GeoCoordinates', 'Google']])
# nur Schweiz
df = df[df["EVSEDataRecord.Address.Country"] == "CHE"]

# new data frame with split value columns
new = df["EVSEDataRecord.GeoCoordinates.Google"].str.split(" ", n = 1, expand = True)
 
# making separate first name column from new data frame
df["lat"] = new[1]
df["lat"] = df["lat"].astype(float)
 
# making separate last name column from new data frame
df["lon"]= new[0]
df["lon"] = df["lon"].astype(float)

df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lat,df.lon))
df = df.set_crs('epsg:4326')

# spatial join
df_join = gpd.sjoin(Schweiz, df, how='right', predicate='intersects')
df = df_join[df_join["UUID"].notnull()]

df_plugs = df['OperatorID'].value_counts().to_frame().reset_index()
df_plugs.rename(columns={"count": "Plugs"}, inplace=True)
df_plugs.rename(columns={"index": "OperatorID"}, inplace=True)

#Zusammenfuehren
df_result = pd.merge(df_standorte, df_ladesaeulen, how="left", on=["OperatorID"])
df_result = pd.merge(df_result, df_plugs, how="left", on=["OperatorID"])
df_result["Datum"]= datetime.today().strftime("%Y-%m-%d")

#Speichern
df_result.to_csv("CPO-Monitoring.csv", header=False, index=False, mode='a')

#Visualisierung
df = pd.read_csv("CPO-Monitoring.csv", parse_dates=['Datum'])
df['Standorte'] = df['Standorte'].astype('int')
df['Ladesaeulen'] = df['Ladesaeulen'].astype('int')
df['Plugs'] = df['Plugs'].astype('int')

attributes = ["Standorte", "Ladesaeulen", "Plugs"]
bigfive = ["CHEVP", "CH*CCC", "CH*ECU", "CH*REP", "CH*SWISSCHARGE"]
otherrealtime = ["CH*AIL","CH*ENMOBILECHARGE","CH*EVAEMOBILITAET","CH*EWACHARGE","CH*FASTNED","CH*IBC","CH*MOBILECHARGE","CH*MOBIMOEMOBILITY","CH*PACEMOBILITY","CH*PARKCHARGE", "CH*SCHARGE", "CH*TAE"]

CPO_dict = {
    "CHEVP": "GreenMotion",
    "CH*CCC": "Move",
    "CH*ECU": "eCarUp",
    "CH*REP": "Plug'n Roll",
    "CH*SWISSCHARGE": "Swisscharge",
    "CH*AIL":"AIL",
    "CH*ENMOBILECHARGE":"en mobilecharge",
    "CH*EVAEMOBILITAET":"EVA E-Mobilität",
    "CH*EWACHARGE":"EWAcharge",
    "CH*FASTNED":"Fastned",
    "CH*IBC":"IBC",
    "CH*MOBILECHARGE":"mobilecharge",
    "CH*MOBIMOEMOBILITY":"Mobimo emobility",
    "CH*PACEMOBILITY":"PAC e-moblity",
    "CH*PARKCHARGE":"PARK & CHARGE",
    "CH*SCHARGE":"S-Charge",
    "CH*TAE":"Matterhorn Terminal Täsch"
}

# Overviews
for attribute in attributes:
    
    # Big Five
    df_all = df[df["OperatorID"].isin(bigfive)]
    df_all = df_all.replace({"OperatorID": CPO_dict})
    df_all = df_all.pivot(index="Datum", columns=["OperatorID"], values=attribute)
    df_all.plot(figsize=(15,10))
    plt.legend(loc='best')
    plt.title("Anzahl " + attribute)
    plt.savefig('plots/Overview-Big5-' + attribute + '.png')
    #plt.show()
    plt.close()   
    
    # Other realtime
    df_all = df[df["OperatorID"].isin(otherrealtime)]
    df_all = df_all.replace({"OperatorID": CPO_dict})
    df_all = df_all.pivot(index="Datum", columns=["OperatorID"],values=attribute)
    df_all.plot(figsize=(15,10))
    plt.legend(loc='best')
    plt.title("Anzahl " + attribute)
    plt.savefig('plots/Overview-otherrealtime-' + attribute + '.png')
    #plt.show()
    plt.close()
    
    # Offline provider
    df_all = df[~df["OperatorID"].isin(bigfive)]
    df_all = df_all.replace({"OperatorID": CPO_dict})
    df_all = df_all[~df_all["OperatorID"].isin(otherrealtime)]
    df_all = df_all.pivot(index="Datum", columns=["OperatorID"],values=attribute)
    df_all.plot(figsize=(15,10))
    plt.legend(loc='best')
    plt.title("Anzahl " + attribute)
    plt.savefig('plots/Overview-offline-' + attribute + '.png')
    #plt.show()
    plt.close()
    
    
# CPOs einzeln
for attribute in attributes:
    for cpo in df["OperatorID"].unique():
        df_cpo = df.copy()
        df_cpo = df_cpo[df_cpo["OperatorID"] == cpo]
        df_cpo = df_cpo.replace({"OperatorID": CPO_dict})
        df_cpo_all = df_cpo.pivot(index="Datum", columns=["OperatorID"],values=attribute)
        df_cpo_all.plot(figsize=(15,10))
        plt.legend(loc='best')
        plt.title("Anzahl " + attribute)
        plt.savefig('plots/' + cpo + '-' + attribute + '.png')
        #plt.show()
        plt.close()