import base64
import io
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import pandas as pd
import pathlib
import pymssql
import datetime
import math
import dash_table
import dash_daq as daq
import argparse
import time
import utilities as uts
import numpy as np

from dash.dependencies import Input, Output, State, ALL, State
from datetime import timedelta
from flask import jsonify

import DIST_MAT_API_CALL as matrix 
import main as algs

import dash_leaflet as dl

# Cool, dark tiles by Stadia Maps.
url = 'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png'
attribution = '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a> '
# Some tile urls.
keys = ["watercolor", "toner", "terrain"]


BASE_DIR = pathlib.Path().absolute().__str__()

group_colors = {"control": "light blue", "reference": "red"}

app = dash.Dash(
    __name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}]
)
server = app.server
app.title="Ruteo UDEM"
tab_height="5hv"
app.config['suppress_callback_exceptions'] = True

def generate_config():
    return html.Div(
        id="markdown",
        className="modal",
        children=(
            html.Div(
                id="markdown-container",
                className="markdown-container",
                children=[
                        html.H5( className="sub", children=["CONTROL CENTER"]),
                        html.Div(id="parametros-objetivo", className='fila', style={'margin-top':'20px'},
                                        children=[
                                                    html.Div(className='celda',children=['Minimization Objective']), 
                                                    html.Div(className='celda', children= [dcc.Dropdown(
                                                                    style={"width":"200px"},
                                                                    className='dropdown-setup',
                                                                    id='objetivos-dropdown',
                                                                    placeholder="...",
                                                                    clearable=False,
                                                                    options=[
                                                                                {'label': 'Multiple', 'value': 'multiple'},
                                                                                {'label': 'Just Time', 'value': 'tiempo'},
                                                                                {'label': 'Just Coverage', 'value': 'cobertura'},   
                                                                            ],
                                                                    value='multiple',
                                                                    
                                                                    )
                                                        ])
                                                ]),
                        html.Div(id="solver", className='fila', style={'margin-top':'0px'},
                                        children=[
                                                    html.Div(className='celda',children=['Alogrithm-solver']), 
                                                    html.Div(className='celda', children= [dcc.Dropdown(
                                                                    style={"width":"200px"},
                                                                    className='dropdown-setup',
                                                                    id='algoritmos-dropdown',
                                                                    placeholder="...",
                                                                    clearable=False,
                                                                    options=[
                                                                                {'label': 'MIP', 'value': 'MIP'},
                                                                                {'label': 'SAVINGS', 'value': 'SAVINGS'},
                                                                                {'label': 'TABU_SEARCH', 'value': 'TS'},
                                                                                {'label': 'SIMMULATED_A', 'value': 'SA'},
                                                                            ],
                                                                    value='MIP',
                                                                    
                                                                    )
                                                        ])
                                                ]), 
                        html.Div(id="switches-params", className='fila', style={'margin-top':'20px'},
                                        children=[
                                                    html.Div(className='celda-switch', children=[daq.BooleanSwitch(
                                                                    on=False,
                                                                    id='nodos-misma-calle',
                                                                    label="Nodes Same Street",
                                                                    color="#ff8c00",
                                                                    )]),
                                                        html.Div(className='celda-switch', 
                                                            children=[
                                                                daq.NumericInput(label='Limit Seconds', id='limite-segundos',value=30, min=10, max=300, size=80)  
                                                                    ]),
                                                    html.Div(className='celda-switch', children=[daq.BooleanSwitch(
                                                                    on=True,
                                                                    id='orden-nodos',
                                                                    label="Asc. order Nodes",
                                                                    color="#ff8c00",
                                                                    )]),
                                                ]),         
                        html.Div(id="numeric-params", className='fila', style={'margin-top':'30px'},
                                        children=[
                                                    html.Div(className='celda-param', 
                                                            children=[
                                                                daq.NumericInput(label='Coverage Weight', id='peso-cobertura',value=10, min=1, max=10, size=70)  
                                                                    ]),
                                                    html.Div(className='celda-param', 
                                                            children=[
                                                                daq.NumericInput(label='Travel Time Weight', id='peso-tiempo',value=1, min=1, max=100, size=70)  
                                                                    ]),
                                                    html.Div(className='celda-param', 
                                                            children=[
                                                                daq.NumericInput(label='Time Before Class', id='tiempo-antes', min=0, value=15, max=200, size=70)  
                                                                    ]),
                                                    html.Div(className='celda-param', 
                                                            children=[
                                                                daq.NumericInput(label='Route Limit Time', id='limite-tiempo',value=65, min=1, max=200, size=70)  
                                                                    ]),
                                                ]), 
                        dcc.Loading(children=[
                        html.Div(
                            className="close-container",
                            children=[
                                html.Div(children=[html.Button(className="saveButton",id="boton-guardar",children='SAVE'), html.Div(id="hidden-div-h") ]),
                                html.Button(
                                "CLOSE",
                                id="markdown_close",
                                n_clicks=0,
                                className="closeButton",
                            ),
                            
                            ]
                        ), ]),
                ],
            )
        ),
    )


# Layout
app.layout = html.Div(
    children=[
        # Titulo
        html.Div(
            className="study-browser-banner row",
            children=[
                html.Div(
                    className="div-logo",
                    children=html.Img(
                        className="logo", src=app.get_asset_url("troy_white.png")
                    ),
                ),
                #html.H2(className="h2-title", children="Optimizador MP"),
                html.Div(className='rounded-corner-title', children=['SMART ROUTING - Universidad de Monterrey']),
                html.H2(className="h2-title-mobile", children="Optimizador MP"), 
                #html.Div(className="dropdown",children=[]),   
                #html.Div(className="seleccion",children=[html.Img(className="engine",src=app.get_asset_url("bars.png"))]),
            ],
        ),
        # Principal
        html.Div(
            className="row app-body",
            children=[      
                html.Div(
                    className="twelve columns card",
                    children=[
                            dcc.Tabs(colors={"primary":"orange","background": "#A0A0A0"}, className='tabs', value='tab-lotes', id='tabs',style={
                                            'width': '30%',
                                            "color":"white",
                                            'font-size': '110%',
                                            'height':tab_height,
                                            "fontFamily": "system-ui",
                                        },
                                        children=[
                                                dcc.Tab(label='Data', value='tab-lotes',style={'padding': '0','line-height': tab_height}, selected_style={'padding': '0','line-height': tab_height}, 
                                                children=[

                                                        #Tabla de ops a optimizar
                                                        html.Div(
                                                                className="nine columns", style={"padding-top":"0px"},
                                                                children=[ 
                                                                        html.Div(className="bg-white", id='tabla-lotes'),
                                                                        dcc.Loading(id='load-carga',children=[html.Div(id='hidden-loading', className='encima', style={'display':'none'})], type="cube", color='#f4511e', fullscreen=True),
                                                                ],
                                                            ),
                                                        #Espacio para seleccionar materiales
                                                        html.Div(
                                                                className="three columns", style={"padding-top":"0px"},
                                                                children=[
                                                                        html.Div(className="bg-white3",
                                                                        children=[
                                                                            html.H5( className="sub", children=["LOAD DATA"]),
                                                                            html.Div(className='tabla',  children=[
                                                                                        html.Div( className='fila', children=[ 
                                                                                                    dcc.Upload(
                                                                                                        id='upload-data',
                                                                                                        children=html.Div([
                                                                                                            'Drag&Drop or ',
                                                                                                            html.A('Import files (xlsx/csv)')
                                                                                                        ]),
                                                                                                        style={
                                                                                                            'width': '90%',
                                                                                                            'height': '50px',
                                                                                                            'lineHeight': '50px',
                                                                                                            'fontSize':'17px',
                                                                                                            'borderWidth': '1px',
                                                                                                            'marginLeft':'20px',
                                                                                                            'borderStyle': 'dashed',
                                                                                                            'borderRadius': '8px',
                                                                                                            'textAlign': 'center',
                                                                                                            'verticalAlign':'middle',
                                                                                                            'marginBottom':'15px',
                                                                                                        },
                                                                                                        # Allow multiple files to be uploaded
                                                                                                        multiple=True
                                                                                                    ),
                                                                                                dcc.Loading(id="load-upload",children=[html.Div(id="upload-div")], type="graph", color="#8b0000", fullscreen=True),
                                                                                                ]),
                                                                                        html.Div(id="ruta", className='fila', style={'marginBottom':'12px'},
                                                                                                children= [ 
                                                                                                            html.Div(className='celda',children=['Select a Route']), 
                                                                                                            html.Div(className='celda', children= [dcc.Dropdown(
                                                                                                                                style={"width":"200px"},
                                                                                                                                className='dropdown-setup',
                                                                                                                                id='rutas-dropdown',
                                                                                                                                placeholder="Optional",
                                                                                                                                clearable=False,
                                                                                                                                
                                                                                                                                )
                                                                                                                        ])
                                                                                                                
                                                                                                            ]),
                                                                                        html.Div(id="optimizar",  className='fila', 
                                                                                        children=[
                                                                                                    html.Div(className='celda', children=[
                                                                                                        dbc.Button(className='button',id='optimizador', children=[html.Span('OPTIMIZE')])
                                                                                                        ])
                                                                                                ]
                                                                                        )
                                                                                        ])
                                                                            ]),  
                                                                        ],
                                                                ),

                                                            #Espacio para seleccionar parametros
                                                            html.Div(
                                                                    className="three columns",
                                                                    children=[
                                                                            html.Div(className="bg-white2" ,children=[
                                                                                html.H5( className="sub", children=["DEMANDS"]),
                                                                                html.Div(id='tabla-demanda'),
                                                                                
                                                                                ]),  
                                                                            ],
                                                                    ),
                                                                    dbc.Button(className='boton-h', id='configuracion', children=['CONFIGURATION']),
                                                    ]),

                                                dcc.Tab(label='Routing', value='tab-resultado',style={'padding': '0','line-height': tab_height}, selected_style={'padding': '0','line-height': tab_height}, 
                                                children=[

                                                        #Tabla de resultado
                                                        html.Div(
                                                                className="nine columns", style={"padding-top":"0px"},
                                                                children=[
                                                                     dcc.Loading(id='load-carga2',children=[
                                                                                html.Div(className="bg-white", id='tabla-resultado',
                                                                                children=[
                                                                                    html.Div([
                                                                                        dl.Map( id='mapa', children=[
                                                                                            dl.LayersControl(
                                                                                                            [dl.BaseLayer(dl.TileLayer(url=url, maxZoom=20, attribution=attribution), 
                                                                                                                        name=key, checked=key == "toner") for key in keys] +
                                                                                                            [dl.Overlay(dl.LayerGroup(id='markers'), name="markers", checked=True)]
                                                                                                        )]
                                                                                            )
                                                                                    ], style={'width': '100%', 'height': '100%', 'margin': "auto", "display": "block", "position": "relative"}),
                                                                                ]),
                                                                                ], type="graph", color="#8b0000"),
                                                                ],
                                                            ),
                                                            #Espacio para ops no asignadas
                                                        html.Div(
                                                                className="three columns", style={"padding-top":"0px"},
                                                                children=[
                                                                        html.Div(className="bg-white3_1",
                                                                        children=[
                                                                            html.H5( className="sub", children=["ORDER OF VISITS"]),
                                                                            html.Div(className='tabla-no-asignados', id='tabla-orden'),
                                                                            ]),  
                                                                        ],
                                                            ),
                                                        html.Div(
                                                                className="three columns", style={"padding-top":"0px"},
                                                                children=[
                                                                        html.Div(className="bg-white2_1",
                                                                        children=[
                                                                            html.H5( className="sub", children=["KEY INDICATORS"]),
                                                                            #html.Div(id='tabla-indicadores'),
                                                                            html.Div(className='tabla',  children=[
                                                                                html.Div(id="barra", className='fila', style={'marginBottom':'15px'},
                                                                                                children= [ 
                                                                                                    daq.GraduatedBar(
                                                                                                            id='barra-cobertura',
                                                                                                            showCurrentValue=True,
                                                                                                            max=100,
                                                                                                            label="Potential Coverage",
                                                                                                            size=400,
                                                                                                        ),                
                                                                                                ]),
                                                                                html.Div(id="barra7", className='fila', style={'marginBottom':'5px'},
                                                                                                children= [ 
                                                                                                        html.Div(className='celda-titulo', children=[
                                                                                                         "Number of Stops"
                                                                                                        ]), 
                                                                                                        html.Div(id='indicador-paradas',className='celda-tiempo-r'),       
                                                                                                ]),  
                                                                                html.Div(id="barra4", className='fila', style={'marginBottom':'5px'},
                                                                                                children= [ 
                                                                                                        html.Div(className='celda-titulo', children=[
                                                                                                         "Travel Time (mins)"
                                                                                                        ]),
                                                                                                        html.Div(id='indicador-tiempo',className='celda-tiempo-r'),             
                                                                                                ]),    
                                                                                html.Div(id="barra3", className='fila', style={'marginBottom':'12px'},
                                                                                                children= [ 
                                                                                                        html.Div(className='celda-titulo', children=[
                                                                                                         "Covered Demand"
                                                                                                        ]),
                                                                                                        html.Div(id='indicador-cobertura',className='celda-tiempo-r')             
                                                                                                ]), 
                                                                                        ]),
                                                                            ]),  
                                                                        ],
                                                            ),
                                                    ]),
                                                
                                                dcc.Tab(label='Scheduling', value='tab-visor',style={'padding': '0','line-height': tab_height}, selected_style={'padding': '0','line-height': tab_height}, 
                                                children=[

                                                        #Visor de piezas en barras
                                                        html.Div(
                                                                className="nine columns", style={"padding-top":"0px"},
                                                                children=[
                                                                    dcc.Loading(id='load-carga3',children=[
                                                                        html.Div(className="bg-white" , children=[
                                                                            dcc.Graph(
                                                                                        id='grafica-scheduling', style={"height" : "100%", "width" : "100%"}
                                                                                     )
                                                                                    ]),
                                                                        ], type='default'),
                                                                    
                                                                ],
                                                            ),
                                                        html.Div(
                                                                className="three columns", style={"padding-top":"0px"},
                                                                children=[
                                                                    dcc.Loading(id='load-carga5',children=[
                                                                        html.Div(className="bg-white3_1",
                                                                        children=[
                                                                            html.H5( className="sub", children=["SCHEDULING TABLE"]),
                                                                            html.Div(className='tabla-no-asignados', id='tabla-horarios')
                                                                            ]),  
                                                                        
                                                                    ], type='default'),
                                                                    ],
                                                            ),
                                                        html.Div(
                                                                className="three columns", style={"padding-top":"0px"},
                                                                children=[
                                                                    dcc.Loading(id='load-carga6',children=[
                                                                        html.Div(className="bg-white2_1",
                                                                        children=[
                                                                            html.H5( className="sub", children=["KEY INDICATORS"]),
                                                                            html.Div(className='tabla',  children=[
                                                                                html.Div(id="barra-coverage-sj", className='fila', style={'marginBottom':'15px'},
                                                                                                children= [ 
                                                                                                    daq.GraduatedBar(
                                                                                                            id='barra-cov1',
                                                                                                            showCurrentValue=True,
                                                                                                            max=100,
                                                                                                            label="Daily Coverage % Route SJ",
                                                                                                            size=400,
                                                                                                        ),                
                                                                                                ]),
                                                                                html.Div(id="barra-coverage-sp", className='fila', style={'marginBottom':'15px'},
                                                                                                children= [ 
                                                                                                    daq.GraduatedBar(
                                                                                                            id='barra-cov2',
                                                                                                            showCurrentValue=True,
                                                                                                            max=100,
                                                                                                            label="Daily Coverage % Route SP",
                                                                                                            size=400,
                                                                                                        ),                
                                                                                                ]),
                                                                                html.Div(id="barra-trip", className='fila', style={'marginBottom':'5px'},
                                                                                                children= [ 
                                                                                                        html.Div(className='celda-titulo', children=[
                                                                                                         "Total Trips"
                                                                                                        ]),
                                                                                                        html.Div(className='celda-titulo', children=[
                                                                                                         "Time Before Class"
                                                                                                        ])             
                                                                                                ]),    
                                                                                html.Div(id="barra-tbc", className='fila', style={'marginBottom':'12px'},
                                                                                                children= [ 
                                                                                                        html.Div(id='indicador-trips',className='celda-tiempo'),
                                                                                                        html.Div(id='indicador-tbc',className='celda-tiempo')             
                                                                                                ]), 
                                                                                        ]),
                                                                            ]),  
                                                                            ],type='default'),
                                                                        ],
                                                            ),
                                                    ]),
                                        ]
                                    ), html.Div(id='h-div-nodos', style={'display':'none'}),
                                       html.Div(id='h-div-demanda', style={'display':'none'}),
                                       html.Div(id='h-div-nodos_opuestos', style={'display':'none'}),
                                       html.Div(id='h-div-horarios', style={'display':'none'}),
                                       html.Div(id='h-div-buses', style={'display':'none'}),
                                       html.Div(id='h-div-api_key', style={'display':'none'}),
                                       html.Div(id='h-div-routing_results', style={'display':'none'}),
                    ],
                ), 
            ],
        ), generate_config(),
    ]
)

def parse_contents(contents, filename, date, sheet=None):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename and not sheet:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
        elif 'xlsx' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded), sheet)
    except Exception as e:
        print(e)
        return html.Div(['There was an error processing this file.'])

    return df

#------------------------------------------------------- GUARDA INFO----------------------------------------------------------------------------------
@app.callback([Output('upload-div', 'children'), Output('h-div-nodos','children'), Output('h-div-demanda','children'), Output('h-div-nodos_opuestos','children'),
                Output('h-div-horarios','children'), Output('h-div-buses','children'),  Output('h-div-api_key','children')],
              [Input('upload-data', 'contents')],
              [State('upload-data', 'filename'),
               State('upload-data', 'last_modified')])
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:

        children = [parse_contents(c, n, d,'NodesCoordinates') for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)]
        nodos=children[0].to_json(date_format='iso', orient='split', default_handler=str)

        children = [parse_contents(c, n, d,'NodesDemands') for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)]
        demandas=children[0].to_json(date_format='iso', orient='split', default_handler=str)

        children = [parse_contents(c, n, d,'ClassesStartTimes') for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)]
        horarios=children[0].to_json(date_format='iso', orient='split', default_handler=str)

        children = [parse_contents(c, n, d,'BusShifts') for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)]
        datos_buses=children[0].to_json(date_format='iso', orient='split', default_handler=str)

        children = [parse_contents(c, n, d,'ApiKey') for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)]
        api_key=children[0].to_json(date_format='iso', orient='split', default_handler=str)

        nodos_opuestos=None

        time.sleep(1)

        return None, nodos, demandas, nodos_opuestos, horarios, datos_buses, api_key
    
    return [None]*7


## LO VA A ACTIVAR EL UPLAD, PARA QUE PASE LOS DATOS AL BROWSER EN LA SESION
#------------------------------------------------------- ACTUALIZA CARGA----------------------------------------------------------------------------------
@app.callback( Output('tabla-lotes', 'children'),
               [Input('h-div-nodos','children')])
def cargar_nodos(json_nodos):
    
    if json_nodos:

        #Mandamos llamar SP de datos
        df=pd.read_json(json_nodos, orient='split',dtype = {"Lat": str,"Long":str})
        df['id']=df['ID_R'] 

        return [dash_table.DataTable(id="tabla-nodos",
                            hidden_columns=["ID_R","id"],
                            css=[{"selector": ".show-hide", "rule": "display: none"}],
                            style_header={
                                    'backgroundColor': "#383838", #"#383838",
                                    "color": "white",
                                    'fontWeight': '400',
                                },
                            data=df.to_dict('records'),
                            columns=[{'id': c, 'name': c, "selectable": True} for c in df.columns],
                            row_selectable="multi",
                            style_as_list_view=True,
                            selected_rows=[],
                            #fixed_rows={"headers":True,"data":0},
                            page_action="native",
                            page_current= 0,
                            fixed_rows={ "headers": True },
                            #fixed_columns={'headers': True, 'data': 1},
                            style_table={
                                        'minHeight': '760px', 'height': '760px', 'maxHeight': '760px',
                                        #'minWidth': '900px', 'width': '900px', 'maxWidth': '900px',
                                        'overflowY': 'auto',
                                        'overflowX': 'auto'
                                    }, 
                            style_cell_conditional=[
                                                {
                                                    'if': {'column_id': c},
                                                    'textAlign': 'center',
                                                    "fontFamily": "system-ui",
                                                    'whiteSpace': 'normal',
                                                    'minWidth':'110px','width': 'auto','maxWidth':'4000px',
                                                    "font-size":"18px"
                                                } for c in df.columns
                                            ]              
                        )]

    return [html.Div(className='no-hay-carga',children=["¡Load Some Data!"])]


## LO VA A ACTIVAR EL UPLAD, PARA QUE PASE LOS DATOS AL BROWSER EN LA SESION
#------------------------------------------------------- ACTUALIZA CARGA----------------------------------------------------------------------------------
@app.callback( Output('tabla-demanda', 'children'),
               [Input('h-div-demanda','children')])
def cargar_demanda(json_nodos):
    
    if json_nodos:

        #Mandamos llamar SP de datos
        df=pd.read_json(json_nodos, orient='split',dtype = {"Lat": str,"Long":str})

        return [dash_table.DataTable(id="tabla-demanda",
                            hidden_columns=["id"],
                            css=[{"selector": ".show-hide", "rule": "display: none"}],
                            style_header={
                                    'backgroundColor':"white", #"#383838",
                                    "color":  "#383838",
                                    'fontWeight': '500',
                                },
                            data=df.to_dict('records'),
                            columns=[{'id': c, 'name': c, "selectable": True} for c in df.columns],
                            style_as_list_view=True,
                            selected_rows=[],
                            #fixed_rows={"headers":True,"data":0},
                            page_action="native",
                            page_current= 0,
                            fixed_rows={ "headers": True },
                            #fixed_columns={'headers': True, 'data': 1},
                            style_table={
                                        'minHeight': '430px', 'height': '430px', 'maxHeight': '430px',
                                        #'minWidth': '900px', 'width': '900px', 'maxWidth': '900px',
                                        'overflowY': 'auto',
                                        'overflowX': 'auto'
                                    }, 
                            style_cell_conditional=[
                                                {
                                                    'if': {'column_id': c},
                                                    'textAlign': 'center',
                                                    "fontFamily": "system-ui",
                                                    'whiteSpace': 'normal',
                                                    'minWidth':'110px','width': 'auto','maxWidth':'4000px',
                                                    "font-size":"18px"
                                                } for c in df.columns
                                            ]              
                        )]

    return [html.Div(className='no-hay-demanda',children=["¡Load Some Data!"])]


#------------------------------------------------------- ACTUALIZA CARGA----------------------------------------------------------------------------------
@app.callback( Output('rutas-dropdown','options'),
               [Input('h-div-nodos','children')])
def cargar_materiales(json_nodos):

        if json_nodos:

            df=pd.read_json(json_nodos, orient='split',dtype = {"Lat": str,"Long":str})
            lista_rutas=df['Route'].unique().tolist()
            rutas=[ {'label': name, 'value': name} for name in lista_rutas]

            return rutas
        
        return  []


#------------------------------------------------------- RENDERIZA HORNOS ---------------------------------------------------------------------------
@app.callback(Output("markdown", "style"),
            [Input("configuracion", "n_clicks"), Input("markdown_close", "n_clicks")])
def update_click_output(button_click, close_click):

    ctx=dash.callback_context
    if ctx.triggered:
        prop_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if prop_id == "configuracion":

            return {"display": "block"}

    return {"display": "none"}



#------------------------------------------------------- DISPONE BOTON DE OPT-----------------------------------------------------------------------------
@app.callback( Output('optimizador','disabled'),[Input('h-div-nodos','children')])
def cargar_boton_optimizar(json_nodos):

        if json_nodos:

            return  False
        
        return True


#------------------------------------------------------- LLAMA OPTIMIZADOR---------------------------------------------------------------------------------
@app.callback( [Output('tabla-orden', 'children'), Output('indicador-tiempo','children'),Output('indicador-cobertura','children')
                , Output('barra-cobertura','value'), Output('indicador-paradas','children'), Output('markers','children'), Output('mapa','center'),Output('mapa','zoom')],
                [Input('optimizador','n_clicks')], 
                [State('h-div-nodos','children'),State('h-div-demanda','children'),State('rutas-dropdown', 'value'),State('algoritmos-dropdown', 'value'), State('tabla-nodos', 'selected_row_ids'),
                 State('objetivos-dropdown','value'), State('limite-segundos','value'), State('peso-tiempo','value'), State('peso-cobertura','value'), 
                 State('limite-tiempo','value'), State('tiempo-antes','value'),State('orden-nodos','on'), State('h-div-api_key','children')] )
def optimizador(optimiza, json_nodos, json_demanda, ruta, algoritmo, selected_row_ids, objetivo, limite_segundos,peso_tiempo,peso_cobertura,limite_tiempo,
                tiempo_antes, orden_nodos, json_api):

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'optimizador' in changed_id and json_demanda and json_nodos:

            #Esto deben ser las ops que a a entrar al algoritmo como df
            df_f= pd.read_json(json_nodos, orient='split')
            df_d= pd.read_json(json_demanda, orient='split')
            API_KEY_DF = pd.read_json(json_api, orient='split')

            if len(API_KEY_DF)>0:
                API_KEY=API_KEY_DF['API_KEY'].tolist()[0]
            else:
                return [None]*6, [25.67,-100.39], 13

            
            if selected_row_ids:             
                df_f=df_f.loc[df_f['ID_R'].isin(selected_row_ids)].reset_index(drop=True)
                df_d=df_d.loc[df_d['ID'].isin(selected_row_ids)].reset_index(drop=True)

            if ruta:
                df_f=df_f[df_f.Route==ruta].sort_values(['Route','Node']).reset_index(drop=True)
                df_d=df_d[df_d.Route==ruta].sort_values(['Route','Node']).reset_index(drop=True)

            #Genereramos lista de nodos para api
            lista_nodos=[ str(df_f.Lat[nodo])+","+str(df_f.Long[nodo]) for nodo in range(len(df_f))]
            matriz_distancias = matrix.matriz_distancias_api('duration',lista_nodos,API_KEY)
            matriz_distancias=(np.asarray(matriz_distancias)/60).astype(int).tolist()  

            #Sorteamos demanda por nodos para que haga sentido el depot
            df_d=df_d.sort_values(['Node']).reset_index(drop=True)
            demands=df_d.Demand.astype(int).tolist()

            #Obtenemos nombres de nodos a optimizar
            df_f=df_f.sort_values(['Node']).reset_index(drop=True)
            lista_nombres=df_f.Name.tolist()
            
            #Corremos optimizador
            df, tiempo_bus_total, demanda_cubierta, tiempo_cpu = algs.optimizador_rutas(algoritmo,matriz_distancias,limite_segundos,demands,False, lista_nombres)

            #Actualizamos indicadores de numero
            tiempo_ruta= str(tiempo_bus_total) 
            cobertura = str(demanda_cubierta) 

            #Actualizamos indicadores de barras
            porcentaje_cobertura=int((demanda_cubierta/sum(demands))*100)
            nodos=str(len(df)-1)
            
            #Cambiar a solo los que resultaron en el df de salida
            markers = [dl.Marker(position=[df_f.Lat[nodo],df_f.Long[nodo]]) for nodo in range(len(df_f))]

            return [dash_table.DataTable(id="tabla-orden",
                            hidden_columns=["id",'Starttimestamp'],
                            css=[{"selector": ".show-hide", "rule": "display: none"}],
                            style_header={
                                    'backgroundColor':"white", #"#383838",
                                    "color":  "#383838",
                                    'fontWeight': '500',
                                },
                            data=df.to_dict('records'),
                            columns=[{'id': c, 'name': c, "selectable": True} for c in df.columns],
                            style_as_list_view=True,
                            selected_rows=[],
                            #fixed_rows={"headers":True,"data":0},
                            page_action="native",
                            page_current= 0,
                            fixed_rows={ "headers": True },
                            #fixed_columns={'headers': True, 'data': 1},
                            style_table={
                                        'minHeight': '340px', 'height': '340px', 'maxHeight': '340px',
                                        #'minWidth': '900px', 'width': '900px', 'maxWidth': '900px',
                                        'overflowY': 'auto',
                                        'overflowX': 'auto'
                                    }, 
                            style_cell_conditional=[
                                                {
                                                    'if': {'column_id': c},
                                                    'textAlign': 'center',
                                                    "fontFamily": "system-ui",
                                                    'whiteSpace': 'normal',
                                                    'minWidth':'110px','width': 'auto','maxWidth':'4000px',
                                                    "font-size":"18px"
                                                } for c in df.columns
                                            ]              
                        )] , tiempo_ruta, cobertura, porcentaje_cobertura, nodos, markers, [25.67,-100.39], 13
        
    return [None]*6, [25.67,-100.39], 13


#---------------------------------------------------------- CAMBIA DE TAB ---------------------------------------------------------------------------------
@app.callback( Output('tabs', 'value'),[Input('optimizador','n_clicks')] )
def cambia_tabs(click):

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'optimizador' in changed_id:

        return 'tab-resultado'

    return 'tab-lotes'


#---------------------------------------------------------- SCHEDULING ---------------------------------------------------------------------------------
@app.callback( [Output('tabla-horarios', 'children'),Output('grafica-scheduling','figure'),Output('barra-cov1','value'),Output('barra-cov2','value'),
                Output('indicador-trips','children'),Output('indicador-tbc','children')],
                [Input('tabs','value')], [State('h-div-buses','children'),State('h-div-horarios','children')])
def programa(tab, buses, horarios):

    if tab=='tab-visor':

        buses = pd.read_json(buses, orient='split')
        horarios =pd.read_json(horarios, orient='split')

        df, fig, coberturas = algs.vrp_scheduling(buses, horarios)

        cov_sj=100
        cov_sp=100

        trips=len(df)

        tbc=15

        return [dash_table.DataTable(id="tablas-horarios",
                            hidden_columns=["id",'Starttimestamp'],
                            css=[{"selector": ".show-hide", "rule": "display: none"}],
                            style_header={
                                    'backgroundColor':"white", #"#383838",
                                    "color":  "#383838",
                                    'fontWeight': '500',
                                },
                            data=df.to_dict('records'),
                            columns=[{'id': c, 'name': c, "selectable": True} for c in df.columns],
                            style_as_list_view=True,
                            selected_rows=[],
                            #fixed_rows={"headers":True,"data":0},
                            page_action="native",
                            page_current= 0,
                            fixed_rows={ "headers": True },
                            #fixed_columns={'headers': True, 'data': 1},
                            style_table={
                                        'minHeight': '340px', 'height': '340px', 'maxHeight': '340px',
                                        #'minWidth': '900px', 'width': '900px', 'maxWidth': '900px',
                                        'overflowY': 'auto',
                                        'overflowX': 'auto'
                                    }, 
                            style_cell_conditional=[
                                                {
                                                    'if': {'column_id': c},
                                                    'textAlign': 'center',
                                                    "fontFamily": "system-ui",
                                                    'whiteSpace': 'normal',
                                                    'minWidth':'110px','width': 'auto','maxWidth':'4000px',
                                                    "font-size":"18px"
                                                } for c in df.columns
                                            ]              
                        )], fig, cov_sj, cov_sp, trips, tbc

    return None, {}, None, None, None, None 

 
if __name__ == "__main__":
    app.run_server(host='0.0.0.0')