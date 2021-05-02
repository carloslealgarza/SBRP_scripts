import pandas as pd
import pymssql
import collections


def transformar_referencias_pesos_segun_qtcs(df):
    
    #----------------------------------------------------------------------------
    #INTERPRETAMOS DATOS DE CALIFICACION Y DEFINIMOS MINIMIZACION A UTILIZAR 
    
    #Listas que indican que tipo de calificacion de colada se refiere (origen o x lingote) 
    refiere_colada_origen=['Colada Origen Hornada por Estandar']
    refiere_colada=['Colada Hornada por Estandar','Colada Hornada - % Muestreo Pruebas Lab',
                    'Colada por Numero de Parte','Colada Hornada por Numero de Parte',
                    'Colada Calificada (No Estandar)','Colada Hornada por Lote de Forja','Colada Hornada']
    
    #TipoRestColada indica que tipo de colada usaremos para minimizar segun indique la calif
            #0: no se incluye en la minimizacion de coladas de ningun tipo
            #1: se minimiza el numero de coladas origen para la OP
            #2: se minimiza el numero de coladas (x lingote) para la op       
    for i in range(len(df)):
        if df['TipoCalif'][i] in refiere_colada:
            df.at[i,'TipoMinColada']=2
        elif df['TipoCalif'][i] in refiere_colada_origen:
            df.at[i,'TipoMinColada']=1
        else: 
            df.at[i,'TipoMinColada']=0
            
    #-----------------------------------------------------------------------------
    #INTERPRETAMOS DATOS DE QTCs PARA DEFINIR EXCESO
            
    #Listas de QTCs que implican variables y combinaciones en algoritmo
    qtc_prolongacion=['Prolongación','Prolongación con Extracción en Torno',
                     'Prolongación Diámetro Exterior','Prolongación Diámetro Interior']
    qtc_sacrificio=['Sacrificio', 'Sacrificio Desarrollo']
    
    #QTCs que implican exceso en algoritmo
    qtc_de_exceso = qtc_prolongacion + qtc_sacrificio
    
    #Agregamos peso de exceso segun QTC 
    for i in range(len(df)):
        if df['TipoQTC'][i] in qtc_prolongacion:
            
            if df['PesoQTC'][i]==0:
                df.at[i,'PesoQTC']=int(1.2*df['Peso'][i])

            #Se calcula el exceso para el peso de prolongacion
            df.at[i,'Exceso']=df['PesoQTC'][i]-df['Peso'][i]  
            #Hacer validacion de que sea mayor?
            
        elif df['TipoQTC'][i] in qtc_sacrificio:
            
            #En este caso el exceso representa el peso completo, por ser sacrificio
            #El algoritmo lo interpreta como un exceso independiente para facilitar el calculo
            df.at[i,'Exceso']=df['Peso'][i]
            
        elif df['TipoQTC'][i]=='Prolongación' and df['TipoCalif'][i] in ['Cada Pieza','Cada Forja']:
            
            if df['PesoQTC'][i]==0:
                df.at[i,'PesoQTC']=int(1.2*df['Peso'][i])

            #Si se prolonga cada pieza, todas las piezas son de peso de QTC
            df.at[i,'Peso']=df['PesoQTC'][i]

        else: 
            #Si no es prolongacion o sacrificio, entonces el exceso es 0
            df.at[i,'Exceso']=0
            
    return df, qtc_de_exceso, qtc_prolongacion, qtc_sacrificio

def validar_datos(df):
    
    ''' Funcion para poner observaciones en donde los datos sean inconsistenetes para la op'''
    
    validaciones=['Peso','PesoQTC','FrecuenciaCU','TipoQTC','TipoCalif','Perfil']
    mensajes=['Pesos','Pesos de QTC','Frecuencias de CU','Tipos de QTC','Calificaciones','Perfiles']
    for i in range(len(df)):
        for j,validacion in enumerate(validaciones):
            if len(df[validacion][i])>1:
                df.at[i,'Observaciones']+= '(Distintos ' + mensajes[j] + ' en la OP) '
            else:
                df.at[i,validacion]=df[validacion][i][0]
                
    return df

def cargar_piezas():
    
    '''Funcion para mandar query a MSSQL para extraer carga actual de piezas y sus propiedades'''
    
    engine = pymssql.connect(server='ffsql1.frisa.com',user='sif20', password='fri$a', database='SIF20')
    QUERY_PIEZAS=''' 
    
    use Sif20
        
    -- Piezas           
    declare @Carga table ( OrdenInterna varchar(200), STD varchar(100), Pieza varchar(100), CatalogoProceso varchar(50), Material varchar(200), FRIMP varchar(500), 
                            Perfil int, TipoQTC varchar(100), TipoCalif varchar(200), Hold bit, Peso float, PesoQTC float, PrioridadCortes int, Demanda int, LoteTT int,
                            Barra uniqueidentifier, Colada uniqueidentifier, FrecuenciaCU varchar(50), CostoQTC float, IDPieza uniqueidentifier, 
                            NumeroParte varchar(200), ID_OP uniqueidentifier, Multiplos int, MultiplosCU int)          
    insert into @Carga(OrdenInterna,Pieza, STD,CatalogoProceso, Material, FRIMP, Perfil, TipoQTC, TipoCalif, Hold, Peso, PesoQTC, PrioridadCortes, 
                        Demanda, LoteTT, Barra, Colada, FrecuenciaCU, CostoQTC, IDPieza, NumeroParte, ID_OP, Multiplos, MultiplosCU)       
    select Distinct    
        OrdenInterna = ordenInterna.Nombre 
        , Pieza = NombrePieza  
        , STD = std.Nombre                                        
        , Process = catProceso.Acronimo   
        , materiales.Nombre
        , frimpMP.Nombre
        , perfilMP.Nombre
        , probetas.Nombre
        , calif.Nombre
        , pza.EstaEnEspera
        , isnull(infopeso.PesoCorte,0) --+ isnull(infopeso.ExcesoProlongacion,0)
        , infopeso.PesoCorteProlongacion--isnull(infopeso.ExcesoProlongacion,0)
        , DATEDIFF(hour,info.FechaCreacion,GETDATE())
        , DemandaReal.valor
        , TT.cantidad_lote
        , pza.Barra
        , pza.Colada
        , frecuenciaCU.Nombre
        , grupomat.CostoQTC
        , IDPieza=pza.ID
        , info.NumeroParte
        , ordenInterna.ID
        , Multiplos = info.NumeroMultiplosHorizontales
        , infolab.MultiploForjaCutUp
    from Sif20..ProduccionInventarioCarga carga (nolock)          
    join Sif20..ProduccionPieza pza (nolock) on pza.ID = carga.Pieza          
    join Sif20..ProductosProducto prod (nolock) on prod.ID = pza.ID and prod.GCRecord is null          
    join Sif20..ProduccionProceso procesoActual (nolock) on procesoActual.ID = carga.Secuencia  
    left join Sif20..ProduccionOperacion operacionActual (nolock) on operacionActual.ID = carga.Operacion          
    left join Sif20..ConfiguradorCatalogoOperacion catOperacion (nolock) on catOperacion.ID = operacionActual.CatalogoOperacion    
    join Sif20..ConfiguradorCatalogoProceso catProceso (nolock) on catProceso.ID = procesoActual.CatalogoProceso        
    left join Sif20..ConfiguradorRutaOperacion rutaOper (nolock) on rutaOper.ID = operacionActual.ID          
    join Sif20..ConfiguradorPlantillasRevision revSTD (nolock) on revSTD.ID = prod.RevisionEstandarActual          
    join Sif20..ConfiguradorPlantillasEstandar std (nolock) on std.ID = revSTD.Estandar          
    join Sif20..ProduccionOrdenesOrden ordenInterna (nolock) on ordenInterna.ID = prod.OrdenProduccionInterna        
    join Sif20..ProduccionInfoGeneral info (nolock) on info.ID = pza.InfoGeneral 
    join Sif20..ProduccionInfoGeneralPeso infopeso (nolock) on infopeso.ID= info.InfoGeneralPeso
    join Sif20..ProduccionInfoGeneralMateriaPrima infoMP (nolock) on infoMP.ID=info.InfoGeneralMateriaPrima
    join Sif20..ProduccionInfoGeneralLaboratorio infolab (nolock) on infolab.ID=info.InfoGeneralLaboratorio
    join Sif20..LaboratorioProbetaTipo probetas (nolock) on probetas.ID=infolab.TipoQTC
    join Sif20..LaboratorioCalificacionTipo calif (nolock) on calif.ID=infolab.TipoCalificacion and calif.GCRecord is null
    join Sif20..LogisticaMateriaPrimaFRIMPsFRIMP frimpMP (nolock) on frimpMP.ID=infoMP.FRIMPPrincipal
    join Sif20..LogisticaMateriaPrimaMaterialPerfilesPerfilFrisa perfilMP (nolock) on perfilMP.ID=infoMP.PerfilOptimo
    join Sif20..LogisticaMateriaPrimaMaterial materiales (nolock) on materiales.ID=frimpMP.Material
    join Sif20..LogisticaMateriaPrimaMaterialGrupo grupomat (nolock) on grupomat.ID=materiales.Grupo
    left join Sif20..ResumenesEspecificacionFrecuenciaCutUp frecuenciaCU (nolock) on frecuenciaCU.ID=infolab.FrecuenciaCutUp
    outer apply(
                select top 1 cantidad_lote=tto.CantidadLote
                from ConfiguradorRutaProceso ruta  
                join Sif20..ProduccionProceso procesoTT WITH(nolock) on procesoTT.ID= ruta.ID and procesoTT.GCRecord is null and procesoTT.CatalogoProceso='076B0FC4-F439-42B1-A93A-36FBB89F4401' --TT
                join Sif20..ProduccionOperacion po  (nolock) on po.Proceso = procesoTT.ID and po.GCRecord is null 
                join Sif20..TratamientoTermicoConfiguracionOperacion tto (nolock) on tto.ID = po.ID 
                where ruta.Producto = carga.Pieza
                order by tto.CantidadLote) TT
    outer apply(select valor=sum(rel.CantidadAsociada)
                from Sif20..ProduccionOrdenesInternasOrdenClienteCubierta rel
                where rel.OrdenInterna=ordenInterna.ID
                ) DemandaReal
    where          
        pza.EstadoProducto not in (9, 10) 
        and pza.Barra is null and pza.Colada is null and pza.PreReceta is null
        --and catProceso.Acronimo in ('CONF','COR','PUL','FOR')
        and infoMP.BarraAsignada is Null and infoMP.ColadaAsignada is Null 
        and catProceso.Acronimo in ('CONF')
        and carga.Sistema = 2
        --and procesoActual.Planta = 'A5EF8BE1-1D64-477A-9CDE-7E554391E289'          
        and  std.ID != '80164B15-9DCB-4725-BD67-1C71C6369E1E' -- STD 10000          
    order by STD
            
    --Regresamos tabla
    select 
    STD,
    OP=OrdenInterna,
    NumeroParte,
    TipoOP='Producción',
    Pieza,
    Material,
    FRIMP,
    Perfil,
    Peso,
    PesoQTC,
    TipoQTC,
    TipoCalif,
    FrecuenciaCU,
    AplicaCU=Null,
    LoteTT,
    PrioridadCortes,
    CostoQTC,
    Hold,
    Demanda,
    Multiplos,
    MultiplosCU,
    IDPieza,
    ID_OP
    from @Carga 
    order by OP, Pieza


    
    ''' 
    df=pd.read_sql(QUERY_PIEZAS, engine)
    
    return df

def cargar_piezas_pronostico(horizonte):
    
    '''Funcion para mandar query a MSSQL para extraer carga FUTURA de piezas y sus propiedades'''
    
    engine = pymssql.connect(server='ffsql1.frisa.com',user='sif20', password='fri$a', database='SIF20')
    QUERY_FORECAST=''' 
    
        use Sif20
        declare @Horizonte_planeacion int
                
        set @Horizonte_planeacion= %s
                
        -- Tabla de Demanda
        declare @Demanda Table(STD varchar(50), OP varchar(200), Cantidad int, FechaLiberacionPiezas datetime, FechaEntrega datetime, UltimaPieza uniqueidentifier,
                                Material varchar(200), FRIMP varchar(200), Perfil int, TipoQTC varchar(200), TipoCalif varchar(200), Peso float, PesoQTC float,
                                FrecuenciaCU varchar(50), LoteTT int, CostoQTC float, NumeroParte varchar(200), ID_OP uniqueidentifier, Multiplos int, MultiplosCU int)
                
        insert into @Demanda
        Select 
            STD = std.Nombre
            , Orden.Nombre
            , CEILING (Orden.Cantidad/CAST(NULLIF(info.NumeroMultiplosHorizontales,0) AS float)) 
            , info.FechaCreacionPiezas
            , orden.FechaEntregaCliente
            , UltimaPiezaCreada.ID_Pieza
            , materiales.Nombre
            , frimpMP.Nombre
            , perfilMP.Nombre
            , probetas.Nombre
            , calif.Nombre
            , isnull(infopeso.PesoCorte,0) --+ isnull(infopeso.ExcesoProlongacion,0)
            , infopeso.PesoCorteProlongacion
            , 'none' -- frecuenciaCU.Nombre --Se sugiere no considerar x ser pronostico
            , 100 --TT.cantidad_lote --Se sugiere no considerar esta restriccion en el modelo porque lo realentiza innecesariamente (por no ser detalle importante)
            , 100 --grupomat.CostoQTC
            , info.NumeroParte
            , orden.ID
            , info.NumeroMultiplosHorizontales
            , infolab.MultiploForjaCutUp
        from ProduccionOrdenesOrden orden
        join ProduccionInfoGeneral info on info.ID = orden.InfoGeneral
        join ConfiguradorPlantillasRevision revSTD on revSTD.ID = orden.RevisionEstandar
        join ConfiguradorPlantillasEstandar std on std.ID = revSTD.Estandar
        outer apply(select count(1) Cantidad
                    from ProductosProducto prod
                    where prod.OrdenProduccionInterna = orden.ID
        )PiezasCreadas
        outer apply(
                    select top 1 ID_Pieza=pza.ID, InfoG=info.ID
                    from ProduccionPieza pza
                    join ProductosProducto prod on prod.ID=pza.ID
                    join ProduccionInfoGeneral info on info.ID=pza.InfoGeneral
                    where prod.RevisionEstandarActual=revSTD.ID and pza.Sistema=2
                    order by info.FechaCreacion desc
                    )UltimaPiezaCreada
        join Sif20..ProduccionInfoGeneralPeso infopeso (nolock) on infopeso.ID= info.InfoGeneralPeso
        join Sif20..ProduccionInfoGeneralMateriaPrima infoMP (nolock) on infoMP.ID=info.InfoGeneralMateriaPrima
        join Sif20..ProduccionInfoGeneralLaboratorio infolab (nolock) on infolab.ID=info.InfoGeneralLaboratorio
        join Sif20..LaboratorioProbetaTipo probetas (nolock) on probetas.ID=infolab.TipoQTC
        join Sif20..LaboratorioCalificacionTipo calif (nolock) on calif.ID=infolab.TipoCalificacion and calif.GCRecord is null
        join Sif20..LogisticaMateriaPrimaFRIMPsFRIMP frimpMP (nolock) on frimpMP.ID=infoMP.FRIMPPrincipal
        join Sif20..LogisticaMateriaPrimaMaterialPerfilesPerfilFrisa perfilMP (nolock) on perfilMP.ID=infoMP.PerfilOptimo
        join Sif20..LogisticaMateriaPrimaMaterial materiales (nolock) on materiales.ID=frimpMP.Material
        --outer apply(
        --			select top 1 cantidad_lote=tto.CantidadLote
        --			from ConfiguradorRutaProceso ruta  
        --			join Sif20..ProduccionProceso procesoTT WITH(nolock) on procesoTT.ID= ruta.ID and procesoTT.GCRecord is null and procesoTT.CatalogoProceso='076B0FC4-F439-42B1-A93A-36FBB89F4401' --TT
        --			join Sif20..ProduccionOperacion po  (nolock) on po.Proceso = procesoTT.ID and po.GCRecord is null 
        --			join Sif20..TratamientoTermicoConfiguracionOperacion tto (nolock) on tto.ID = po.ID 
        --			where ruta.Producto = UltimaPiezaCreada.ID_Pieza
        --			order by tto.CantidadLote) TT
                
        where orden.Sistema = 2 and orden.Tipo = 3 and orden.Estado = 8
        and orden.GCRecord is null
        and PiezasCreadas.Cantidad = 0
        and info.FechaCreacionPiezas <= GETDATE()+@Horizonte_planeacion --A cuantos dias planear
        and orden.Cantidad > 0
        --order by 1, FechaCreacionPiezas
                
        select 
        STD,
        OP,
        NumeroParte,
        TipoOP='PorLiberar',
        Piezas=REVERSE(SUBSTRING(REVERSE(REPLICATE(STD+'-X,', Cantidad)), 2, 9999)),
        Cantidad,
        Material,
        FRIMP,
        Perfil,
        Peso,
        PesoQTC,
        TipoQTC,
        TipoCalif,
        FrecuenciaCU,
        AplicaCU=Null,
        LoteTT,
        CostoQTC=100,
        Hold=0,
        Demanda=Cantidad*Multiplos,
        Multiplos,
        MultiplosCU,
        PrioridadCortes=1,
        Observaciones=Null,
        IDPieza=UltimaPieza,
        ID_OP
        from @Demanda
        order by Material, Perfil, STD, FechaLiberacionPiezas
    
     '''
    df=pd.read_sql(QUERY_FORECAST%(horizonte), engine)
    
    return df

def cargar_barras_op(pieza_base):
    
    '''Funcion para mandar query a MSSQL para extraer barras disponibles para carga actual y sus propiedades'''
    
    engine = pymssql.connect(server='ffsql1.frisa.com',user='sif20', password='fri$a', database='SIF20')
    QUERY=''' usp_MateriaPrima_TraeBarrasValidasPorPieza '%s', %s '''  
    df=pd.read_sql(QUERY%(str(pieza_base),0), engine)
    
    return df

def cargar_barras_op_pronostico(op):
    
    '''Funcion para mandar query a MSSQL para extraer barras disponibles para carga FUTURA y sus propiedades'''
    
    engine = pymssql.connect(server='ffsql1.frisa.com',user='sif20', password='fri$a', database='SIF20')
    QUERY=''' usp_MateriaPrima_TraeBarrasValidasPorOP '%s', %s '''  
    df=pd.read_sql(QUERY%(str(op),0), engine)
    
    return df

def obtener_barras(df):
    
    '''Funcion que ayuda a agrupar las barras y crear un diccionario de relacion op-barra
    para simplificar su manejo en el algoritmo'''
    
    #Construimos diccionario de OPs y sus barras validas
    relBarrasOp=collections.defaultdict(list)
    
    #Creamos dataframe para llenar con barras disponibles
    df_bars=pd.DataFrame(columns=['IDBarra','NombreBarra','ColadaOrigen','Colada','Material','FRIMP','Perfil','PesoDisponible',
                                  'AntiguedadDias','CostoKg','PesoOriginal','Merma','MetodoFabricacion','PesoSobrante'])
    
    for i in range(len(df)):
        if df['Observaciones'][i]=='':
            if df['TipoOP'][i]=='Producción':
                barras_validas=cargar_barras_op(str(df['IDPieza'][i]))
            else:
                barras_validas=cargar_barras_op_pronostico(str(df['ID_OP'][i]))
            if len(barras_validas)==0: 
                df.at[i,'Observaciones']= 'No tiene barras disponibles'
            elif barras_validas['PesoDisponible'].sum() < df['Peso'][i]*df['Cantidad'][i]: 
                df.at[i,'Observaciones']='Peso Insuficiente de Barras'
            else: 
                relBarrasOp[df['OP'][i]]=barras_validas['IDBarra'].tolist()
                df_bars=pd.concat([df_bars,barras_validas]).drop_duplicates(['IDBarra'],keep='last').reset_index(drop=True)

    return df, df_bars, relBarrasOp

#-----------------------------------------------------------------------------
#Graficamos en gantt para visualizacion de aprovechamiento
from plotly.offline import plot
import plotly.express as px

def graficar_piezas(dfx,dfb):
    
    '''Funcion que grafica las piezas en las barras, con sus sobrantes y aprovechamiento'''
    
    #Copiamos info y creamos df de sobrantes para desplegar
    dfm=dfx.copy()

    if len(dfm)==0:
        return {}
        
    dfs=pd.DataFrame(columns=dfm.columns)
    df_sobrantes=dfb.loc[dfb['Seleccionada']==1].reset_index(drop=True)
    dfs['Aprovechamiento']=''
    for i in range(len(df_sobrantes)): dfs.loc[len(dfs)]=['Sobrante','Sobrante',df_sobrantes['IDBarra'][i],df_sobrantes['NombreBarra'][i],
                                                          df_sobrantes['FRIMP'][i],'NA',df_sobrantes['PesoDisponible'][i],0,0,0,df_sobrantes['Aprovechamiento'][i]]
    
    #Obtenemos utilizacion promedio de barras para imprimir en visor
    if len(dfb['Aprovechamiento'].loc[dfb['Seleccionada']==1])>0:
        utilizacion_promedio=dfb['Aprovechamiento'].loc[dfb['Seleccionada']==1].mean()
    else:
        utilizacion_promedio=0
    
    #Agregamos texto para colocar sobre cada pieza en el visor
    for i in range(len(dfm)):
    
        if dfm['EsProlongación'][i]==1: dfm.at[i,'Texto']=' '+str(dfm["Pieza"][i])+' (P) '
        elif dfm['EsSacrificio'][i]==1: dfm.at[i,'Texto']=' '+str(dfm["Pieza"][i])+' (S) '
        elif dfm['EsCutup'][i]==1: dfm.at[i,'Texto']=' '+str(dfm["Pieza"][i])+' (C) '
        else: dfm.at[i,'Texto']=str(dfm["Pieza"][i])
    
    #Definimos colores customizados para llenar ops
    custom_color_sequence=['#3283FE', '#0D2A63', '#85660D', '#782AB6', '#565656', '#1C8356', 
                           '#2CA0C2', '#EE7600', '#808080', '#1CBE4F', '#C4451C', '#F58518', '#E45756', 
                           '#325A9B', '#FEAF16', '#3232FF', '#90AD1C', '#F6222E', '#FFA15A', '#636EFA',
                           '#222A2A', '#C075A6', '#17BEFC', '#B00068', '#FBE426']
    
    #Creamos grafica
    fig = px.bar(dfm, x="Peso", y="NombreBarra", color='OP', orientation='h',
                 hover_data=["FRIMP"],
                 title='Optimización de barras: ' + str(round(utilizacion_promedio*100,3)) + '%', 
                 text='Texto',
                 color_discrete_sequence=custom_color_sequence)

    fig.update_traces(opacity=0.8)
    
    #Agregamos subgrafica de sobrantes
    if len(dfs)>0:
        fig2 = px.bar(dfs,x='Peso',y='NombreBarra',color='OP',orientation='h',color_discrete_sequence=['#8B0000'], hover_data=["Aprovechamiento"])
        fig.add_trace(fig2.data[0])
    
    #Ordenamos por categoria
    fig.update_yaxes(categoryorder='total descending')
    
    #Ploteamos con texto en medio
    fig.update_traces(textposition='inside', insidetextanchor="middle", insidetextfont=dict(color='white'))
    #plot(fig) 

    return fig

#Definimos funcion para segmentar problema en subproblemas
def segmentar_problema(df,criterio,limite):
    contador=0
    indices=[]
    for i in range(len(df)):
        contador+=int(df[criterio][i])
        if contador > limite:
            indices.append(i)
            contador=0
    indices.append(len(df))
    
    if len(indices)>1:
        l = indices
        l_mod = [0] + l + [max(l)+1]
        list_of_dfs = [df.iloc[l_mod[n]:l_mod[n+1]] for n in range(len(l_mod)-2)] 
        for i in range(len(list_of_dfs)):list_of_dfs[i]=list_of_dfs[i].reset_index(drop=True) 
    else:
        list_of_dfs = [df]
    
    return list_of_dfs

def cargar_barras_op_mostrar(pieza_base):
    
    '''Funcion para mandar query a MSSQL para extraer barras disponibles para carga actual y sus propiedades'''
    
    engine = pymssql.connect(server='ffsql1.frisa.com',user='sif20', password='fri$a', database='SIF20')
    QUERY=''' usp_MateriaPrima_TraeBarrasValidasPorPieza '%s', %s '''  
    df=pd.read_sql(QUERY%(str(pieza_base),1), engine)
    
    return df

def cargar_barras_op_pronostico_mostrar(op):
    
    '''Funcion para mandar query a MSSQL para extraer barras disponibles para carga FUTURA y sus propiedades'''
    
    engine = pymssql.connect(server='ffsql1.frisa.com',user='sif20', password='fri$a', database='SIF20')
    QUERY=''' usp_MateriaPrima_TraeBarrasValidasPorOP '%s', %s '''  
    df=pd.read_sql(QUERY%(str(op),1), engine)
    
    return df