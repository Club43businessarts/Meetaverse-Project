try:
    import asyncio
except ImportError:
    raise RuntimeError("This requries at least Python3.4/asyncio")

#LIBRARIES
#from geopy import distance
from faker import Faker
from geopy import distance
#import time
import random
from flask import Flask, render_template, request

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.embed import server_document
#from bokeh.layouts import column
from bokeh.models import ColumnDataSource#, Slider
from bokeh.plotting import figure
from bokeh.server.server import BaseServer
from bokeh.server.tornado import BokehTornado
from bokeh.server.util import bind_sockets
from bokeh.themes import Theme
#from bokeh.sampledata.sea_surface_temperature import sea_surface_temperature


#import requests
#import json
import pandas as pd
from bokeh.models import HoverTool,LabelSet
from bokeh.tile_providers import get_provider, STAMEN_TERRAIN
import numpy as np
#from bokeh.server.server import Server
#from bokeh.application import Application
#from bokeh.application.handlers.function import FunctionHandler
#from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, TableColumn, DataTable
#from bokeh.io import show
#from bokeh.io import output_file
#from bokeh.plotting import figure
from bokeh.layouts import gridplot

#from bokeh.models import HTMLTemplateFormatter



app = Flask(__name__)


#########
#AJUSTES#
#########

#Seleccionar tiempo de refresh (s)
refresh=2

#Ajustar velocidad
multiplo=0.2

#Radio (m)
radius=500

#Usuarios totales
USERS_TOTAL=100

#Usuarios totales
LOCALES_TOTAL=10

# Porcentaje de amigos (%)
por=10

#Definicion cuadrante del mapa
lat_min=39.4505101
lat_max=39.4939737
lon_min=-0.4
lon_max=-0.341


vehicles=["Bike","Train","Car", "Walking"]

faker = Faker('es_ES')



####################################################################
####################################################################

#FUNCTION TO CONVERT GCS WGS84 TO WEB MERCATOR
#DATAFRAME
def wgs84_to_web_mercator(df, lon="lon", lat="lat"):
    k = 6378137
    df["x"] = df[lon] * (k * np.pi/180.0)
    df["y"] = np.log(np.tan((90 + df[lat]) * np.pi/360.0)) * k
    return df

#POINT
def wgs84_web_mercator_point(lon,lat):
    k = 6378137
    x= lon * (k * np.pi/180.0)
    y= np.log(np.tan((90 + lat) * np.pi/360.0)) * k
    return x,y

#COORDINATE CONVERSION
xy_min=wgs84_web_mercator_point(lon_min,lat_min)
xy_max=wgs84_web_mercator_point(lon_max,lat_max)

#COORDINATE RANGE IN WEB MERCATOR
x_range,y_range=([xy_min[0],xy_max[0]], [xy_min[1],xy_max[1]])

#USER TRACKING FUNCTION
def modify_doc(doc):
        
    flask_args = doc.session_context.request.arguments
    # YO Position
    yo_source = ColumnDataSource({'lat':[],'lon':[],'x':[],'y':[],'usuario':[],'match':[],'distance':[]})
    
    yo = pd.DataFrame([{'lon': (lon_min+lon_max)/2, 'lat': (lat_min+lat_max)/2,'usuario': 'Yo','match': 0,'distance':0}])  
    yo=wgs84_to_web_mercator(yo)
    
    n_rollyo=len(yo.index)
    yo_source.stream(yo.to_dict(orient='list'),n_rollyo)
    
    # LOCALES
    # El nombre del local es 'usuario' para que funcione el hover del raton en el mapa. Y el 'match' es la valoracion del local
    locales_source = ColumnDataSource({'usuario':[],'lat':[],'lon':[],'distance':[],'match':[],'x':[],'y':[]})
    locales = pd.DataFrame(columns=('usuario','lat','lon','distance','match'))

    for i in range(LOCALES_TOTAL):
        data = [faker.company(),random.uniform(lat_min, lat_max),random.uniform(lon_min, lon_max),0,str(random.randint(0, 5))+'/5']
        position_local=(data[1],data[2])
        distance1=int(distance.distance((yo.iat[0,1],yo.iat[0,0]), position_local,).m)
        data[3]=distance1
        locales.loc[i] = [item for item in data]
    locales=wgs84_to_web_mercator(locales)
    
    n_rolllocales=len(locales.index)
    locales_source.stream(locales.to_dict(orient='list'),n_rolllocales)
    
    # Usuarios y amigos
    
    users_source = ColumnDataSource({'usuario':[],'lat':[],'lon':[],'distance':[],'friends':[],'transport':[],'match':[],'x':[],'y':[]})
    amigos_source=ColumnDataSource({'usuario':[],'lat':[],'lon':[],'distance':[],'friends':[],'transport':[],'match':[],'x':[],'y':[]})
    noamigos_source=ColumnDataSource({'usuario':[],'lat':[],'lon':[],'distance':[],'friends':[],'transport':[],'match':[],'x':[],'y':[]})
    
    users = pd.DataFrame(columns=('usuario','lat','lon','distance','friends','transport','match','x','y'))
    
    for i in range(USERS_TOTAL):
        name=faker.first_name()
        last_name=faker.last_name()
        username="@"+name.replace(" ","")+last_name.replace(" ","")
        data = [username,random.uniform(lat_min, lat_max),random.uniform(lon_min, lon_max),0,0,random.choice(vehicles),str(random.randint(0, 100))+'%',0,0]

        if random.randint(0, 10)<=(10-por/10):
            data[4]=0
        else:
            data[4]=1
        users.loc[i] = [item for item in data]
        
    # AMIGOSCERCA
    
    amigoscerca_source = ColumnDataSource({'usuario':[]})
    
    
    # UPDATING USERS DATA
    def update():
        
        # AMIGOSCERCA
    
        amigoscerca = pd.DataFrame(columns = ['usuario'])
        
        for i in range(USERS_TOTAL):
            lat=users.iat[i,1]
            lon=users.iat[i,2]
            # Modifica las coordenadas en cada iteracion para simular movimiento segun el tipo de transporte
            if users.iat[i,5] == "Walking":
                users.iat[i,2]=lon+random.uniform(-0.0005, 0.0005)*multiplo
                users.iat[i,1]=lat+random.uniform(-0.0005, 0.0005)*multiplo
            if users.iat[i,5] == "Bike":
                users.iat[i,2]=lon+random.uniform(-0.0005, 0.0005)*multiplo*2
                users.iat[i,1]=lat+random.uniform(-0.0005, 0.0005)*multiplo*2
            if users.iat[i,5] == "Car":
                users.iat[i,2]=lon+random.uniform(-0.0005, 0.0005)*multiplo*3
                users.iat[i,1]=lat+random.uniform(-0.0005, 0.0005)*multiplo*3
            if users.iat[i,5] == "Train":
                users.iat[i,2]=lon+random.uniform(-0.0005, 0.0005)*multiplo*4
                users.iat[i,1]=lat+random.uniform(-0.0005, 0.0005)*multiplo*4
            # Si se salen del cuadrante, respawn aleatorio
            if lat>lat_max or lat<lat_min:
                users.iat[i,2]=random.uniform(lat_min, lat_max)
                users.iat[i,5]=random.choice(vehicles)
            if lon>lon_max or lon<lon_min:
                users.iat[i,2]=random.uniform(lon_min, lon_max)
                users.iat[i,5]=random.choice(vehicles)
            #DISTANCIA QUE SE ACTUALIZA
            position_user=(lat,lon)
            users.iat[i,3]=int(distance.distance(((lat_min+lat_max)/2,(lon_min+lon_max)/2), position_user,).m)
            
            if users.iat[i,3] <= radius:  #if users.iat[i,4] == 1 and users.iat[i,5] == 'Walking' and users.iat[1,3] <= radius:
                add=pd.DataFrame([users.iat[i,0]], columns = ['usuario'])
                amigoscerca = pd.concat([amigoscerca, add], ignore_index=True)
        wgs84_to_web_mercator(users)
        
        # CREATE DATAFRAME WITH ONLY AMIGOS
        amigos = users.loc[users['friends'] == 1]
        
        # CREATE DATAFRAME WITH no AMIGOS
        noamigos = users.loc[users['friends'] == 0]
        
        # CONVERT TO BOKEH DATASOURCE AND STREAMING
        n_roll=len(users.index)
        users_source.stream(users.to_dict(orient='list'),n_roll)
        
        n_rollamigos=len(amigos.index)
        amigos_source.stream(amigos.to_dict(orient='list'),n_rollamigos)
        
        n_rollnoamigos=len(noamigos.index)
        noamigos_source.stream(noamigos.to_dict(orient='list'),n_rollnoamigos)
        
        n_rollamigoscerca=len(amigoscerca.index)
        amigoscerca_source.stream(amigoscerca.to_dict(orient='list'),n_rollamigoscerca)
        
        
    #CALLBACK UPATE IN AN INTERVAL
    doc.add_periodic_callback(update, refresh*1000) #5000 ms/10000 ms for registered user
    
    #PLOT USERS POSITION
    p=figure(x_range=x_range,y_range=y_range,x_axis_type='mercator',y_axis_type='mercator',sizing_mode='fixed',plot_height=740,plot_width=1000)
    tile_prov=get_provider(STAMEN_TERRAIN)
    p.add_tile(tile_prov,level='image')
    p.circle('x','y',source=amigos_source,fill_color='#0057E9',hover_color='white',size=12,fill_alpha=1,line_width=0)
    p.circle('x','y',source=noamigos_source,fill_color='#4d6b53',hover_color='white',size=10,fill_alpha=1,line_width=0)
    p.circle('x','y',source=yo_source,fill_color='#FF00BD',hover_color='white',size=15,fill_alpha=1,line_width=0)
    p.circle('x','y',source=yo_source,fill_color='#FF00BD',hover_color='white',size=105*radius/500,fill_alpha=0.1,line_width=1)
    p.square_dot('x','y',source=locales_source,fill_color='#404040',hover_color='white',size=17,fill_alpha=1,line_width=0)

    #ADD HOVER TOOL AND LABEL
    my_hover=HoverTool()
    my_hover.tooltips=[('Name','@usuario'),('Match','@match'),('Distance (m)','@distance')]
    labels = LabelSet(x='x', y='y', text='', level='glyph', x_offset=0, y_offset=0, source=users_source, render_mode='canvas',background_fill_color='#0057E9',text_font_size="1pt")
    p.add_tools(my_hover)
    p.add_layout(labels)
    
    #LOCALES TABLE
    
    columnslocales = [
            TableColumn(field='usuario', title='Local'),
            TableColumn(field='distance', title='Distance (m)'),
            TableColumn(field='match', title='Rate')
            ]

    q = DataTable(source=locales_source, columns=columnslocales, width=350, height=280)

    # AMIGOSCERCA TABLE
    columnsamigoscerca = [TableColumn(field='usuario', title='USER')]
    
    r = DataTable(source=amigoscerca_source, columns=columnsamigoscerca, width=350, height=280)
    
    s = gridplot([[q],[r]],toolbar_options={'logo': None})
    
    # TOTAL DASHBOARD
    
    #doc.title='MEETAVERSE'
    t = gridplot([[p, s]],toolbar_options={'logo': None})
    doc.theme = Theme(filename="theme.yaml")
    doc.add_root(t)
  



bkapp = Application(FunctionHandler(modify_doc))

sockets, port = bind_sockets("127.0.0.1", 0)

@app.route('/', methods=['GET'])
def bkapp_page():
    dataset = request.args.get('dataset')
    
    script = server_document(
      'http://127.0.0.1:%d/bkapp' % port
    )

    return render_template(
      "index.html", 
      script = script, 
      app_name = "MEETAVERSE",      
      dataset = dataset
      )

def bk_worker():
    asyncio.set_event_loop(asyncio.new_event_loop())

    bokeh_tornado = BokehTornado({'/bkapp': bkapp}, extra_websocket_origins=["127.0.0.1:8000"])
    bokeh_http = HTTPServer(bokeh_tornado)
    bokeh_http.add_sockets(sockets)

    server = BaseServer(IOLoop.current(), bokeh_tornado, bokeh_http)
    server.start()
    server.io_loop.start()

from threading import Thread
Thread(target=bk_worker).start()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug = True)
