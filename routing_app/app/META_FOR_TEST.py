#---- MODELOS PARA TESTS -------------

"""Vehicles Routing Problem (VRP)."""


from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np
import pandas as pd
import random
import time


def vrp_metaheuristic(metaheuristic, Cij, limite_segundos, demands, bloquear_nodos_cercanos):
    """Solve the CVRP problem."""
    
    #Importamos nodos que son compartidos
    if bloquear_nodos_cercanos:
        nodos_compartidos=pd.read_excel(r'C:\Users\carlos.leal\Desktop\PEF\Demanda_Nodos.xlsx','NodesInDisjunction')
        nodos_compartidos=[(random.randint(0,len(Cij)-1),random.randint(0,len(Cij)-1)) for par in range(int(len(Cij)*0.5))]
    
    #Importamos matriz de tiempos
    #Cij=(np.asarray(Cij)/60).tolist()
   
    #Parametros
    tiempo_limite_ruta = 65
    tiempos_servicio = [0] + [5]*(len(Cij)-1)    
    
    def create_data_model(cost_matrix, demands, service_times):
        """Stores the data for the problem."""
        data = {}
        data['time_matrix'] = cost_matrix
        data['demands'] = demands
        data['service_time']=service_times
        data['num_vehicles'] = 1
        data['depot'] = 0
        return data
    
    #Creamos diccionario de datos
    data = create_data_model(Cij, demands, tiempos_servicio)

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
        return data['time_matrix'][from_node][to_node] + data['service_time'][from_node]

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
    
    for node in range(1, len(data['time_matrix'])):
        penalty = data['demands'][node-1]*10000
        routing.AddDisjunction([manager.NodeToIndex(node)],penalty )
        
    if bloquear_nodos_cercanos:
        for pair in nodos_compartidos:
            routing.solver().Add(routing.ActiveVar(manager.NodeToIndex(pair[0])) + routing.ActiveVar(manager.NodeToIndex(pair[1]))<=1)
        #constraintActive = routing.ActiveVar(manager.NodeToIndex(pair[0])) * routing.ActiveVar(manager.NodeToIndex(pair[1]))
        #routing.solver().Add(
        #    constraintActive * routing.VehicleVar(manager.NodeToIndex(pair[0])) != 
        #    constraintActive * routing.VehicleVar(manager.NodeToIndex(pair[1])))
    
    #count_dimension_name = 'count'
    # assume some variable num_nodes holds the total number of nodes
    #routing.AddConstantDimension(
    #    1, # increment by one every time
    #    len(data['time_matrix'])+1,  # make sure the return to depot node can be counted
    #    True,  # set count to zero
    #    count_dimension_name)
    #count_dimension = routing.GetDimensionOrDie(count_dimension_name)
    
    #for node in range(1, len(data['time_matrix'])-1):
        #routing.solver().Add(routing.VehicleVar(manager.NodeToIndex(node)) ==
        #   routing.VehicleVar(manager.NodeToIndex(node+1)))
    #    routing.solver().Add(count_dimension.CumulVar(manager.NodeToIndex(node)) <=
    #       count_dimension.CumulVar(manager.NodeToIndex(node+1)))
    
    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.SAVINGS)
    
    # Metaheuristico
    if metaheuristic=='TABU_SEARCH':
        search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH)
    elif metaheuristic=='SIMULATED_ANNEALING':
        search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING)
    elif metaheuristic=='GUIDED_LOCAL_SEARCH':
        search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)

    # Solve the problem.
    search_parameters.time_limit.FromSeconds(limite_segundos)
    
    start=time.time()
    solution = routing.SolveWithParameters(search_parameters)
    end=time.time()
    
    def obtain_time(data, manager, routing, solution):
        """Prints solution on console."""
        max_route_time = 0
        demanda_cubierta=0
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            #plan_output = 'Ruta de vehiculo {}:\n'.format(vehicle_id)
            route_time = 0
            while not routing.IsEnd(index):
                #plan_output += ' {} -> '.format(manager.IndexToNode(index))
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_time += routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id)
                demanda_cubierta+= data['demands'][previous_index]
            #plan_output += '{}\n'.format(manager.IndexToNode(index))
            #plan_output += 'Tiempo de ruta: {} min\n'.format(route_time)
            #plan_output += 'Demanda cubierta: {} personas\n'.format(demanda_cubierta)
            #print(plan_output)
            max_route_time = max(route_time, max_route_time)
        return max_route_time, demanda_cubierta

    # Print solution on console.
    if solution:
        tiempo, demanda = obtain_time(data, manager, routing, solution)
        return tiempo, demanda, end-start
    
    return 0, 0, end-start
        