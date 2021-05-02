#--------------------------- VRP SCHEDULING MIP -------------------------------

# Objetivo: Programar rutas respecto a horarios y demandas por horario 

# Autores: Carlos Leal y Carlos Gomez
# Institución: Universidad de Monterrey
# email: carlos.lealg@udem.edu

#-----------------------------------------------------------------------------
#Importamos librerias relevantes

import collections
from ortools.linear_solver import pywraplp
import time
import datetime
from datetime import timedelta
import pandas as pd
import numpy as np
import plotly.figure_factory as ff
from plotly.offline import plot
import plotly.graph_objs as go
import random

#-----------------------------------------------------------------------------
#DATOS ENTRADA

def vrp_scheduling(buses, horarios):

    demandas_cubiertas_rutas={'SJ':48, 'SP':22}
    
    datos_buses=buses
    hora_inicio_turno = datos_buses.ShiftStartTime.tolist()
    hora_fin_turno = datos_buses.ShiftEndTime.tolist()
    inicio_modelo = datos_buses.ShiftStartTime.sort_values().tolist()[0]
    capacidades = dict(zip(datos_buses.Bus,datos_buses.Capacity))
    
    #Cuando tienes que llegar a la escuela en cada horario
    datos_horarios=horarios
    
    lista_horarios_original=datos_horarios.StartTime.tolist()
    
    datos_horarios['Demanda'] = datos_horarios.Route.map(demandas_cubiertas_rutas)
    datos_horarios.Demanda = (datos_horarios.PercentageOfDemand * datos_horarios.Demanda).apply(np.ceil).astype(int)
    demandas = dict(zip(datos_horarios.Class,datos_horarios.Demanda))
    
    #-----------------------------------------------------------------------------
    #SOLVER   
    solver = pywraplp.Solver('VRPTW',
                             pywraplp.Solver.SAT_INTEGER_PROGRAMMING)
    
    #GRAN M
    M=100000
    
    inicio_turno=collections.defaultdict()
    fin_turno=collections.defaultdict()
    
    #-----------------------------------------------------------------------------
    #PARAMS
    
    tiempo_colchon= timedelta(minutes=15) #Cuanto tiempo antes llegar a la clase
    numero_limite_viajes=8 #Viajes limite por bus
    maximo_tiempo_antes_clase=30 #Cuanto es lo maximo que se puede llegar antes a la clase
    max_slack=5000 
    numero_descansos=1
    tiempo_descanso=60
    tiempo_servicio = datos_horarios.RouteDuration.tolist()
    
    #-----------------------------------------------------------------------------
    #PRE-PROCESAMIENTOS
    
    #Numero de vehiculos
    numero_vehiculos= len(capacidades)
    
    #Numero de horarios
    nodos=len(lista_horarios_original)+1
    
    for bus in range(numero_vehiculos):
        inicio_turno[bus]=int( (hora_inicio_turno[bus]-inicio_modelo).total_seconds() / 60 )
        fin_turno[bus]=int( (hora_fin_turno[bus]-inicio_modelo).total_seconds() / 60 )
    
    lista_horarios=[]
    for i in range(len(lista_horarios_original)): lista_horarios.append(lista_horarios_original[i]-tiempo_colchon)
    
    lista_horarios_ref = [ int((lista_horarios[i]-inicio_modelo).total_seconds()/60) 
                      for i in range(len(lista_horarios_original))
                      ]
    
    #-----------------------------------------------------------------------------
    #VARIABLES
    X=collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(dict)))
    A=collections.defaultdict(lambda: collections.defaultdict(dict))
    D=collections.defaultdict(lambda: collections.defaultdict(dict))
    diferencias=[]
    
    #Creamos variables 
    for destino in range(nodos):
        for bus in range(numero_vehiculos):
            D[destino][bus] = solver.IntVar(inicio_turno[bus],fin_turno[bus],'')
            A[destino][bus] = solver.IntVar(inicio_turno[bus],fin_turno[bus],'')
            
            #Definimos relacion entre llegada y salida para depot y otros nodos
            if destino>0:
                solver.Add(A[destino][bus] + tiempo_servicio[destino-1] == D[destino][bus])
            else:
                solver.Add(D[destino][bus]<=A[destino][bus])
    
            for origen in range(nodos):         
                X[origen][destino][bus] = solver.BoolVar('')
                
    #Para modelo dinámico
    #for destino in range(1,nodos-1):
    #    for bus in range(numero_vehiculos):
    #            solver.Add(A[destino][bus]<=A[destino+1][bus])
                
    #------------------------------------------------------------------------------
    #CONSTRUCCION DE MODELO
    
    descansos=collections.defaultdict(list)
    #Definimos restriccion de llegadas y salidas en relacion con tiempos de viaje
    for origen in range(nodos):
        for destino in range(nodos):   
            for bus in range(numero_vehiculos):
                if origen!=destino:
                    slack = solver.IntVar(0,max_slack, '')
                    if destino>=4 and origen >=4 and destino<=20 and origen<=20:
                        descanso=solver.BoolVar('')
                        solver.Add( slack >= tiempo_descanso*descanso)
                        solver.Add( X[origen][destino][bus] >= descanso)
                        descansos[bus].append(descanso)
                        
                    solver.Add( D[origen][bus] + slack - M*(1-X[origen][destino][bus]) <= A[destino][bus] )
                    solver.Add( D[origen][bus] + slack + M*(1-X[origen][destino][bus]) >= A[destino][bus] )
    
    #Se agrega binaria para definir si se visita ruta o no a la hora
    demandas_incompletas=[]
    demandas_decode=collections.defaultdict()
    for destino in range(1,nodos):
        drop = solver.BoolVar('')
        demanda_insatisfecha=solver.IntVar(0,sum(demandas.values()),'')
        solver.Add( sum([X[origen][destino][bus] for origen in range(nodos) for bus in range(numero_vehiculos) if destino!=origen]) <= numero_vehiculos*(1-drop))
        solver.Add( sum([X[origen][destino][bus] for origen in range(nodos) for bus in range(numero_vehiculos) if destino!=origen]) >= (1-drop))
        solver.Add( demanda_insatisfecha >= demandas[destino] - sum([X[origen][destino][bus] for origen in range(nodos) for bus in range(numero_vehiculos) if destino!=origen])*capacidades[0])
        demandas_incompletas.append(demanda_insatisfecha*1000)
        demandas_decode[destino]=demanda_insatisfecha
        
    #Agregamos restricciones de buses
    buses_utilizados=[]
    nodos_fuera_de_ruta=[]
    for bus in range(numero_vehiculos):
          
        solver.Add(sum(descansos[bus])>=numero_descansos)
    
        for destino in range(nodos):
            
            no_bus = solver.BoolVar('')
            solver.Add( sum([X[origen][destino][bus] for origen in range(nodos)])== 1-no_bus )
            buses_utilizados.append(1-no_bus)
            
            if destino>0:
                diferencia = solver.IntVar(0,maximo_tiempo_antes_clase,'')
                solver.Add(D[destino][bus] + diferencia <= lista_horarios_ref[destino-1] + M*(no_bus))
                solver.Add(D[destino][bus] + diferencia >= lista_horarios_ref[destino-1] - M*(no_bus))
                diferencias.append(diferencia)
                
                if datos_buses['AssignedRoute'][bus]!=datos_horarios['Route'][destino-1]:
                    nodos_fuera_de_ruta.append(1-no_bus)
            
        #Limitamos numero de viajes de bus
        solver.Add( sum([X[origen][destino][bus] for origen in range(nodos) for destino in range(nodos) if destino!=origen and destino>0]) <= numero_limite_viajes)
        
        #Definimos restriccionde flujo por cada nodo
        for origen in range(nodos):
            solver.Add( sum([X[origen][destino][bus] for destino in range(nodos)]) == 
                        sum([X[destino][origen][bus] for destino in range(nodos)]) )
    
    #Minimizamos
    solver.Minimize(sum(diferencias) + sum(demandas_incompletas) + sum(buses_utilizados)
                    + sum(nodos_fuera_de_ruta)*10 )
    
    #-----------------------------------------------------------------------------
    # DEFINIMOS PARAMETROS DE SOLVER Y LLAMAMOS
    
    #Definimos tiempo limite
    solver.SetTimeLimit(10*1000)
    
    #Llamammos al solver y medimos tiempo CPU
    start=time.time()
    status = solver.Solve()
    end=time.time()
    
    #-----------------------------------------------------------------------------
    #EXTRACCIÓN DE SOLUCIÓN
    
    data_table=[]
    for bus in range(numero_vehiculos):
        for origen in range(nodos):   
            if origen > 0:
                if sum([X[origen][destino][bus].solution_value() for destino in range(nodos)]) >0:
                    data_table.append(['Van '+str(bus), datos_horarios['Route'][origen-1], 
                                       str( (inicio_modelo+timedelta(minutes=A[origen][bus].solution_value())).strftime("%H:%M:%S")),
                                       str( (inicio_modelo+timedelta(minutes=D[origen][bus].solution_value())).strftime("%H:%M:%S")),
                                       lista_horarios_original[origen-1].strftime("%H:%M:%S")
                                        ])
    
    df_resultado=pd.DataFrame(data_table, columns=['Van','Route','Start','End','Class Hour'])   
        
    data=[]
    for bus in range(numero_vehiculos):
        for origen in range(nodos):   
            if origen > 0:
                if sum([X[origen][destino][bus].solution_value() for destino in range(nodos)]) >0:
                    data.append(['Van '+str(bus),lista_horarios_original[origen-1].strftime("%H:%M:%S")  ,inicio_modelo+timedelta(minutes=A[origen][bus].solution_value()),inicio_modelo+timedelta(minutes=D[origen][bus].solution_value()),datos_horarios['Route'][origen-1] ])
        
    
    datos_horarios['Demanda_Insatisfecha']=datos_horarios.apply(lambda row: demandas_decode.get(row.Class).solution_value(), axis=1)  
    
    coberturas=collections.defaultdict()
    rutas=datos_horarios.Route.unique().tolist()
    for ruta in rutas:
        demanda_no_cubierta=datos_horarios[datos_horarios.Route==ruta].Demanda_Insatisfecha.sum()
        demanda_total=datos_horarios[datos_horarios.Route==ruta].Demanda.sum()
        porcentaje=(1-demanda_no_cubierta/demanda_total)
        coberturas[ruta]=porcentaje
    
    dfg=pd.DataFrame(data, columns=['Van','Horario','Inicio','Fin','Ruta'])

    
    df2=[]
    for i in range(len(dfg)):
        df2.append(dict(Task=dfg["Van"][i], Start=dfg["Inicio"][i], Finish=dfg["Fin"][i], Resource=dfg['Van'][i],Description=dfg['Horario'][i]))
    
    
    colors={}
    color_list=['rgb(119,158,203)','rgb(255,158,20)','rgb(105,105,105)','rgb(139,0,0)']
    for i,van in enumerate(dfg['Van'].unique().tolist()):
        #r,g,b=str(random.randint(0,255)),str(random.randint(0,255)),str(random.randint(0,255))
        colors.update( {van:color_list[i]})
    
    
    fig = go.Figure(ff.create_gantt(df2, colors=colors, index_col='Resource', title='Programación de Vans',
                          show_colorbar=True, group_tasks=True, bar_width=0.45, showgrid_x=True, showgrid_y=True, height=760))
    
    posicion={}
    for i,van in enumerate(reversed(dfg['Van'].unique().tolist())):
        posicion.update({van:i})
    
    for i in range(len(dfg)):
        fig['layout']['annotations'] += tuple([dict(x=dfg["Inicio"][i]+(dfg['Fin'][i]-dfg["Inicio"][i])/2,y=posicion.get(dfg['Van'][i]),text=str(dfg["Ruta"][i]), showarrow=False, font=dict(color='white', size=20))])
    
    
    shapes= [{
        "type": "line",
        "x0": hora_inicio_turno[0],
        "y0": "-1",
        "x1": hora_inicio_turno[0],
        "y1": "60",
        'line': {
                    'color': 'orange',
                    'width': 2,
                },
        },
        {
        "type": "line",
        "x0": hora_fin_turno[0],
        "y0": "-1",
        "x1": hora_fin_turno[0],
        "y1": "60",
        'line': {
                    'color': 'orange',
                    'width': 2,
                },
        },
        {
        "type": "line",
        "x0": hora_inicio_turno[1],
        "y0": "-1",
        "x1": hora_inicio_turno[1],
        "y1": "60",
        'line': {
                    'color': 'rgb(62,95,138)',
                    'width': 2,
                },
        },
        {
        "type": "line",
        "x0": hora_fin_turno[1],
        "y0": "-1",
        "x1": hora_fin_turno[1],
        "y1": "60",
        'line': {
                    'color': 'rgb(62,95,138)',
                    'width': 2,
                },
        },
        ]
    
    fig.update_traces(opacity=0.9)
    fig["layout"]["shapes"]=shapes
    
    return df_resultado, fig, coberturas


        