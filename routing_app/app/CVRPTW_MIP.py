#------------------------------ CVRPTW MIP -----------------------------------

# Objetivo: Minimizar duracion de ruta maxima y maximizar cobertura de 
# lugares con alta demanda, para a la vez reducir el numero de viajes
# (no necesariamente el consumo)

# Autores: Carlos Leal y Carlos Gomez
# Institución: Universidad de Monterrey
# email: carlos.lealg@udem.edu

#-----------------------------------------------------------------------------
#Importamos librerias relevantes

from ortools.linear_solver import pywraplp
import collections
import datetime
from datetime import timedelta
import pandas as pd
import numpy as np
import time
import random

def solve_vrp_mip(Cij, limite_segundos, demandas, bloquear_nodos_cercanos,nombres):
    

    tiempo_servicio =  5
    tiempo_limite_ruta = 65
    #Cij=(np.asarray(Cij)/60).tolist()
    parejas_overlap=[]

    try:
        dff = pd.DataFrame(Cij)
        dff.to_excel('example_duration_matrix.xlsx',index=False)
    except:
        pass
    
            
    #-----------------------------------------------------------------------------
    #SOLVER   
    solver = pywraplp.Solver('VRPTW',
                             pywraplp.Solver.SAT_INTEGER_PROGRAMMING)
    #GRAN M
    M=100000

    #-----------------------------------------------------------------------------
    #DATOS ENTRADA
    numero_vehiculos= 1
    hora_inicio_turno= datetime.datetime(2020,9,18,5,35)
    hora_inicio_clase= datetime.datetime(2020,9,18,7,40)
    tiempo_limite_minutos = int( (hora_inicio_clase-hora_inicio_turno).total_seconds() / 60 )
    nodos=len(Cij)

    #-----------------------------------------------------------------------------
    #VARIABLES
    X=collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(dict)))
    A=collections.defaultdict(lambda: collections.defaultdict(dict))
    D=collections.defaultdict(lambda: collections.defaultdict(dict))

    #Creamos variables 
    for destino in range(nodos):
        for bus in range(numero_vehiculos):
            D[destino][bus] = solver.IntVar(0,tiempo_limite_minutos,'')
            A[destino][bus] = solver.IntVar(0,tiempo_limite_minutos,'')

            #Definimos relacion entre llegada y salida para depot y otros nodos
            if destino>0:
                solver.Add(A[destino][bus] + tiempo_servicio == D[destino][bus])
            else:
                solver.Add(D[destino][bus]<=A[destino][bus])
                solver.Add(D[destino][bus]==0)

            #if destino==1:
            #    solver.Add(A[destino][bus]==6)

            for origen in range(nodos):         
                X[origen][destino][bus] = solver.BoolVar('')

    #------------------------------------------------------------------------------
    #CONSTRUCCION DE MODELO

    #Definimos restriccion de llegadas y salidas en relacion con tiempos de viaje
    for origen in range(nodos):
        for destino in range(nodos):   
            for bus in range(numero_vehiculos):
                if origen!=destino:
                    solver.Add( D[origen][bus] + int(Cij[origen][destino]) - M*(1-X[origen][destino][bus]) <= A[destino][bus] )
                    solver.Add( D[origen][bus] + int(Cij[origen][destino]) + M*(1-X[origen][destino][bus]) >= A[destino][bus] )

    #Todos los clientes pueden ser visitados al menos una vez, no importa el bus
    nodos_saltados=[]
    for destino in range(1,nodos):
        drop = solver.BoolVar('')
        nodos_saltados.append(drop*demandas[destino]*1000)
        solver.Add( sum([X[origen][destino][bus] for origen in range(nodos) for bus in range(numero_vehiculos) if destino!=origen])== 1-drop )

    #Definimos t max
    tmax=solver.IntVar(0,tiempo_limite_minutos,'')

    #Agregamos restricciones de buses
    for bus in range(numero_vehiculos):
        
        for destino in range(nodos):
        
            no_bus = solver.BoolVar('')
            solver.Add( sum([X[origen][destino][bus] for origen in range(nodos)])== 1-no_bus )
        
        if bloquear_nodos_cercanos:
            for pareja in parejas_overlap:
                solver.Add( sum([X[origen][destino][bus] for origen in range(nodos) for destino in pareja if origen!=destino]) <= 1)      
        
        tiempo_ruta=sum([X[origen][destino][bus]*Cij[origen][destino] for origen in range(nodos) for destino in range(nodos) if origen!=destino])
        tiempo_restriccion_servicio=sum([X[origen][destino][bus]*tiempo_servicio for origen in range(nodos) for destino in range(nodos) if origen!=destino and destino>0])
        solver.Add( tiempo_ruta + tiempo_restriccion_servicio <= tiempo_limite_ruta )


        #Definimos restriccion de ruta maxima
        solver.Add(tmax>=A[0][bus])

        #Definimos restriccionde flujo por cada nodo
        for origen in range(nodos):
            solver.Add( sum([X[origen][destino][bus] for destino in range(nodos)]) == 
                        sum([X[destino][origen][bus] for destino in range(nodos)]) )

    #Minimizamos
    solver.Minimize(tmax + sum(nodos_saltados))

    #-----------------------------------------------------------------------------
    # DEFINIMOS PARAMETROS DE SOLVER Y LLAMAMOS

    #Definimos tiempo limite
    solver.SetTimeLimit(limite_segundos*1000)
    
    start=time.time()
    status = solver.Solve()
    end=time.time()


    #-----------------------------------------------------------------------------
    #Guardamos rutas en diccionarios                         
        
    if status == pywraplp.Solver.OPTIMAL or status==pywraplp.Solver.FEASIBLE :

        data=[]
        for bus in range(numero_vehiculos):
            for origen in range(len(Cij)):   
                if origen==0:
                    if sum([X[origen][destino][bus].solution_value() for destino in range(nodos)]) >0:
                        data.append([bus,nombres[origen],str( (hora_inicio_turno+timedelta(minutes=D[origen][bus].solution_value())).strftime("%H:%M:%S")),
                                    str( (hora_inicio_turno+timedelta(minutes=A[origen][bus].solution_value())).strftime("%H:%M:%S")), hora_inicio_turno+timedelta(minutes=D[origen][bus].solution_value())])
                else:
                    if sum([X[origen][destino][bus].solution_value() for destino in range(nodos)]) >0:
                        data.append([bus,nombres[origen],str( (hora_inicio_turno+timedelta(minutes=A[origen][bus].solution_value())).strftime("%H:%M:%S")),
                                    str( (hora_inicio_turno+timedelta(minutes=D[origen][bus].solution_value())).strftime("%H:%M:%S")), hora_inicio_turno+timedelta(minutes=A[origen][bus].solution_value())])

        df_resultado = pd.DataFrame(data, columns=['Van','NombreNodo','Inicio','Fin','Starttimestamp'])
        df_resultado = df_resultado.sort_values('Starttimestamp').reset_index(drop=True)

        for bus in range(numero_vehiculos):
            tiempo_viaje=sum([X[origen][destino][bus].solution_value()*Cij[origen][destino] for origen in range(nodos) for destino in range(nodos) if origen!=destino])
            tiempo_total_servicio=tiempo_servicio*sum([X[origen][destino][bus].solution_value() for origen in range(nodos) for destino in range(nodos) if origen!=destino and destino>0])
            tiempo_bus_total=(tiempo_viaje + tiempo_total_servicio)
             
        demanda_cubierta=0
        for bus in range(numero_vehiculos):
            cobertura=sum([demandas[destino]*X[origen][destino][bus].solution_value() for destino in range(nodos) for origen in range(nodos) if destino>0])
            demanda_cubierta+=cobertura
            
        return df_resultado, tiempo_bus_total, demanda_cubierta, end-start

    df_resultado = pd.DataFrame(columns=['Van','NombreNodo','Inicio','Fin','Starttimestamp'])

    return df_resultado, 0, 0, end-start
  



     