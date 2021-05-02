
import pandas as pd
import utilities as uts
from CVRPTW_MIP import solve_vrp_mip
from scheduling import vrp_scheduling


def optimizador_rutas(algoritmo, Cij, limite_segundos, demands, bloquear_nodos, nombres):

    if algoritmo=='MIP':

        #Solo si es MIP Aplicamos Regla
        demandas = {}
        for k,d in enumerate(demands):
                demandas.update({k:d})

        print("Optimizando ...")
        df, tiempo_bus_total, demanda_cubierta, tiempo_cpu  = solve_vrp_mip(Cij, limite_segundos, demandas, bloquear_nodos, nombres)
        print("Optimizado!!")

    return df, tiempo_bus_total, demanda_cubierta, tiempo_cpu


def optimizador_programacion():

    df, fig, coberturas = vrp_scheduling()

    return df, fig, coberturas 

