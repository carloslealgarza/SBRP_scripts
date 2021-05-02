# SBRP_scripts

## There are two folders:

1. "benchmark_tests" contains a script named "experimentos.py", which by running it, all benchmarks are tested and within 30 hours you could get all tests done. They are written in the .txt file named "resultados_test.txt" as a json. 

1. "routing_app" contains a dockerized web application for routing and scheduling. Inside this folder, you can find an excel file named "RoutingInfoInput.xlsx" which you can drag and drop or upload to the web application. This file contains all the information needed to do the routing and scheduling. It is important to have an API KEY from google cloud platform in order to be able to run the routing with real distances and durations. 
