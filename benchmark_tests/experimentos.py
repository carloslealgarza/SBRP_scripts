import json
import utilities_sbrp as uts
import numpy as np
import time

#Documentar que se adapto de benchmarks
#Documentar parametros de metaheuristicos utilizados por ORTOOLS
#Correr hasta optimo
#Poner referencias de uso de los metodos aqui utilizados

files=['Benchmarks/E-n23-k3.txt','Benchmarks/E-n22-k4.txt','Benchmarks/E-n30-k3.txt',
      'Benchmarks/E-n51-k5.txt','Benchmarks/E-n76-k7.txt','Benchmarks/E-n76-k8.txt',
      'Benchmarks/E-n76-k10.txt','Benchmarks/E-n76-k14.txt','Benchmarks/E-n101-k8.txt',
      'Benchmarks/E-n101-k14.txt','Benchmarks/M-n200-k16.txt']

uts.generate_datasets(files)

with open('resultados_test.txt') as json_file:
    nombres = json.load(json_file)
 
exactos=['MIP'] #
metaheuristicos=['SA','TS','GD','LS'] #
heuristicos=['SAVINGS','CHRISTOFIDES'] #'SAVINGS','CHRISTOFIDES'
metodos = exactos + metaheuristicos + heuristicos
    
#%%
for metodo in metodos:
    for instance_name in nombres.keys(): 
        
        with open('resultados_test.txt') as json_file:
            datos = json.load(json_file)
        
        #Capacidades
        capacidad=datos[instance_name]['general']['capacity']
        capacidades = [capacidad]*datos[instance_name]['general']['buses']   #Number of elements in this list is the number of buses!
        tiempo_servicio =  0
        tiempo_limite_ruta = 9999999
        solver_time_limit=1800 #Seconds
        
        #Demandas
        parejas_overlap=None
        demandas = datos[instance_name]['demandas']
        demandas = {int(k):int(v) for k,v in demandas.items()}
        metaheuristico= metodo if metodo in metaheuristicos else None
        heuristico= metodo if metodo in heuristicos else 'SAVINGS' #Si es metaheuristico, se usa savings
        
        #Cij
        Cij = datos[instance_name]['matrix']
        
        #Si el metodo es MIP
        if metodo=='MIP':
            capacidades = {i:capacidad for i in range(datos[instance_name]['general']['buses'])} #Transformation for the model
            tiempo_servicio =  0
            tiempo_limite_ruta = None
            Cij = np.array(Cij)/10

            try:

                start=time.time()
            
                #Run Model
                routes, times =uts.solve_vrp_mip(Cij, capacidades, tiempo_servicio, demandas, tiempo_limite_ruta, 
                                      parejas_overlap,solver_time_limit)

                end=time.time()

                cpu_time=end-start
            except:

                routes, times = None, None

                cpu_time=None
        
        if metodo!='MIP':

            start=time.time()
           
            #Run Model
            routes, times = uts.heuristic_vrp(Cij, capacidades, demandas, tiempo_limite_ruta, 
                                              solver_time_limit, metaheuristico, heuristico)

            end=time.time()

            cpu_time=end-start
            
        if routes and times:
            datos[instance_name]['general']['resultados'].update({ metodo: {'objetivo': sum(times.values()),'cpu_time':cpu_time} })
        else:
            datos[instance_name]['general']['resultados'].update({metodo:None})
        
        with open('resultados_test.txt', 'w') as outfile:
            json.dump(datos, outfile)


