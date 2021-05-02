from __future__ import print_function
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np
import pandas as pd
import json
from ortools.linear_solver import pywraplp
import collections
import datetime
from datetime import timedelta



def heuristic_vrp(Cij, capacidades,demandas,tiempo_limite_ruta, solver_time_limit, 
                  metaheuristico,heuristico):
    """Solve the CVRP problem."""
    
    def create_data_model(cost_matrix, demands, capacidades):
        """Stores the data for the problem."""
        data = {}
        data['time_matrix'] = cost_matrix
        data['demands'] = demandas
        data['num_vehicles'] = len(capacidades)
        data['vehicle_capacities'] = capacidades
        data['depot'] = 0
        return data
    
    #Creamos diccionario de datos
    data = create_data_model(Cij, demandas, capacidades)

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(len(data['time_matrix']),
                                           data['num_vehicles'], data['depot'])

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)


    # Create and register a transit callback.
    def time_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['time_matrix'][from_node][to_node] 

    transit_callback_index = routing.RegisterTransitCallback(time_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Distance constraint.
    dimension_name = 'Time'
    routing.AddDimension(
        transit_callback_index,
        0,  # no slack
        tiempo_limite_ruta,  # vehicle maximum travel time
        True,  # start cumul to zero
        dimension_name)
    time_dimension = routing.GetDimensionOrDie(dimension_name)
    time_dimension.SetGlobalSpanCostCoefficient(100)
    
     # Add Capacity constraint.
    def demand_callback(from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(
        demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        data['vehicle_capacities'],  # vehicle maximum capacities
        True,  # start cumul to zero
        'Capacity')
    
    for node in range(1, len(data['time_matrix'])):
        penalty = data['demands'][node-1]*10000
        routing.AddDisjunction([manager.NodeToIndex(node)],penalty )
        
    #for pair in nodos_compartidos:
    #    routing.solver().Add(routing.ActiveVar(manager.NodeToIndex(pair[0])) + routing.ActiveVar(manager.NodeToIndex(pair[1]))<=1)
    
    # Setting first solution heuristic.
    if heuristico=='CHRISTOFIDES':
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.CHRISTOFIDES) 
    else: #SAVINGS
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.SAVINGS)
    
    # Metaheuristico
    if metaheuristico=='TS':
        search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH)
    elif metaheuristico=='SA':
        search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING)
    elif metaheuristico=='GD':
        search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GREEDY_DESCENT)
    elif metaheuristico=='LS':
        search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)

    # Solve the problem.
    search_parameters.time_limit.FromSeconds(solver_time_limit)
    solution = routing.SolveWithParameters(search_parameters)
    
    def print_solution(data, manager, routing, solution):
        """Prints solution on console."""
        total_distance = 0
        total_load = 0
        times={}
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
            route_distance = 0
            route_load = 0
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                route_load += data['demands'][node_index]
                plan_output += ' {0} Personas({1}) -> '.format(node_index, route_load)
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += round(routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id)/10,2)
            plan_output += ' {0} Personas({1})\n'.format(manager.IndexToNode(index),
                                                     route_load)
            plan_output += 'Tiempo ruta: {}min\n'.format(route_distance)
            plan_output += 'Demanda cubierta ruta: {}\n'.format(route_load)
            #print(plan_output)
            times.update({vehicle_id:route_distance})

        return times
        
    def extract_routes(num_vehicles, manager, routing, solution):
        routes = {}
        for vehicle_id in range(num_vehicles):
            routes[vehicle_id] = []
            index = routing.Start(vehicle_id)
            while not routing.IsEnd(index):
                routes[vehicle_id].append(manager.IndexToNode(index))
                previous_index = index
                index = solution.Value(routing.NextVar(index))
            routes[vehicle_id].append(manager.IndexToNode(index))
        return routes

    # Print solution on console.
    if solution:
        times=print_solution(data, manager, routing, solution)
        
        return extract_routes(data['num_vehicles'], manager, routing, solution), times
    
    return None, None
    
    
def generate_datasets(files):

    datos={}
    for file in files:
        
        content=[]                             
        with open (file, 'rt') as myfile:    
            for myline in myfile:                   
                content.append(myline.rstrip('\n'))
        
        general={}
        coordenadas={}
        demandas={}
        coord=False
        demands=False
        for con in content:
    
            if "CAPACITY" in con:
                general.update({'capacity': int(con.split(' : ')[1])})
    
            if "COMMENT" in con:
                general.update({'buses': int(  con.split(' : ')[1].rstrip(')').lstrip('(').split(',')[1].split(':')[1].lstrip(' ')  )})
                general.update({'optimal': int(  con.split(' : ')[1].rstrip(')').lstrip('(').split(',')[2].split(':')[1].lstrip(' ')  )})
    
            if "NODE_COORD_SECTION" in con:
                coord=True
    
            if "DEMAND_SECTION" in con:
                coord=False
                demands=True
    
            if "DEPOT_SECTION" in con:
                demands=False
    
            if coord and "NODE_COORD_SECTION" not in con:
                cords=con.split(' ')
                coordenadas.update({int(cords[0])-1:(int(cords[1]),int(cords[2]))}) 
    
            if demands and "DEMAND_SECTION" not in con:
                dem=con.split(' ')
                demandas.update({int(dem[0])-1:int(dem[1])}) 
        
        instance_name = file.split('/')[1].split('.')[0]
        datos.update({instance_name:{ 'general': general, 'coordenadas': coordenadas, 'demandas': demandas}})
        
        matrix=[]
        for origen in datos[instance_name]['coordenadas'].values():
            dist_row=[]
            for destino in datos[instance_name]['coordenadas'].values():
                dist_row.append(int(round(((destino[0]-origen[0])**2 + (destino[1]-origen[1])**2)**0.5,2)*10))
            matrix.append(dist_row)
            
        datos[instance_name].update({'matrix':matrix})
        datos[instance_name]['general'].update({'resultados': {}})
        
    with open('resultados_test.txt', 'w') as outfile:
        json.dump(datos, outfile)
        

#Function to be called in order to solve VRP
def solve_vrp_mip(Cij, capacidades, tiempo_servicio, demandas, tiempo_limite_ruta, parejas_overlap, time_limit):
    
    #-----------------------------------------------------------------------------
    #SOLVER   
    solver = pywraplp.Solver('VRPTW',
                             pywraplp.Solver.SAT_INTEGER_PROGRAMMING)
    #GRAN M
    M=100000

    #-----------------------------------------------------------------------------
    #DATOS ENTRADA
    numero_vehiculos= len(capacidades)
    hora_inicio_turno= datetime.datetime(2020,9,18,5,35)
    hora_inicio_clase= datetime.datetime(2020,9,18,10,20)
    tiempo_limite_minutos = 99999 # int( (hora_inicio_clase-hora_inicio_turno).total_seconds() / 60 )
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
    #tmax=solver.IntVar(0,tiempo_limite_minutos,'')

    #Lista de bus visita nodo
    bus_visita_nodo=collections.defaultdict(lambda: collections.defaultdict(dict))

    #Agregamos restricciones de buses
    for bus in range(numero_vehiculos):
        
        for destino in range(nodos):
        
            no_bus = solver.BoolVar('')
            solver.Add( sum([X[origen][destino][bus] for origen in range(nodos)])== 1-no_bus )
        
        #If the distance is less than 5 units
        if parejas_overlap:
            for pareja in parejas_overlap:
                solver.Add( sum([X[origen][destino][bus] for origen in range(nodos) for destino in pareja if origen!=destino]) <= 1)      
        
        if tiempo_limite_ruta:
            tiempo_ruta=sum([X[origen][destino][bus]*Cij[origen][destino] for origen in range(nodos) for destino in range(nodos) if origen!=destino])
            tiempo_restriccion_servicio=sum([X[origen][destino][bus]*tiempo_servicio for origen in range(nodos) for destino in range(nodos) if origen!=destino and destino>0])
            solver.Add( tiempo_ruta + tiempo_restriccion_servicio <= tiempo_limite_ruta )

        #Definimos restriccion para asegurar que no se exceda la capacidad
        solver.Add( sum([X[origen][destino][bus]*demandas[destino] for origen in range(nodos) for destino in range(nodos) if origen!=destino and destino>0]) 
                     <= capacidades[bus]  )

        #Definimos restriccion de ruta maxima
        #solver.Add(tmax>=A[0][bus])

        #Definimos restriccionde flujo por cada nodo
        for origen in range(nodos):
            solver.Add( sum([X[origen][destino][bus] for destino in range(nodos)]) == 
                        sum([X[destino][origen][bus] for destino in range(nodos)]) )

    #Minimizamos
    #tmax + sum(nodos_saltados)
    suma = sum([X[origen][destino][bus]*Cij[origen][destino] for origen in range(nodos) for destino in range(nodos) for bus in range(numero_vehiculos) if origen!=destino])
    solver.Minimize(suma + sum(nodos_saltados))

    #-----------------------------------------------------------------------------
    # DEFINIMOS PARAMETROS DE SOLVER Y LLAMAMOS

    #Definimos tiempo limite
    solver.SetTimeLimit(time_limit*1000)
    status = solver.Solve()
     
              
    if status == pywraplp.Solver.OPTIMAL or status==pywraplp.Solver.FEASIBLE:

        #-----------------------------------------------------------------------------
        #Guardamos rutas en diccionarios

        routes=collections.defaultdict(list)
        for bus in range(numero_vehiculos):
            origen=0
            routes[bus].append(0)
            for viaje in range(int(sum([X[origen][destino][bus].solution_value() for destino in range(nodos) for origen in range(nodos) if origen!=destino]))):
                for destino in range(len(Cij)):
                    if X[origen][destino][bus].solution_value()==1:
                        routes[bus].append(destino)
                        origen=destino
                        break

        print("Optimal Solution Found:") 
        print("")
        times=collections.defaultdict()
        for bus in range(numero_vehiculos):
            tiempo_viaje=sum([X[origen][destino][bus].solution_value()*Cij[origen][destino] for origen in range(nodos) for destino in range(nodos) if origen!=destino])
            tiempo_total_servicio=tiempo_servicio*sum([X[origen][destino][bus].solution_value() for origen in range(nodos) for destino in range(nodos) if origen!=destino and destino>0])
            tiempo_bus_total=(tiempo_viaje + tiempo_total_servicio)
            #print("Time of bus " + str(bus) + ': ' + str(tiempo_bus_total) + " minutes.")
            times[bus]=tiempo_bus_total
            
        #Print covered Demand
        demanda_cubierta=0
        for bus in range(numero_vehiculos):
            cobertura=sum([demandas[destino]*X[origen][destino][bus].solution_value() for destino in range(nodos) for origen in range(nodos) if destino>0])
            #print("Covered demand per route : " + str(cobertura))
            demanda_cubierta+=cobertura

    else:
        routes=None
        times=None

    return routes, times