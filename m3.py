#libs:
import pypsa
import numpy as np
import pandas as pd

#data
dk_dem=[2,2] #Demand, GWh
dk_cf=[] #DK, capacity factor
dk_cf.append( [1, 0.8, 0.5, 0.25, 0.8] )  #DK-1
dk_cf.append( [0.5, 0.4, 0.3, 0.2, 0.1] ) #DK-2

osw_ccost=910 #€/kW
pvs_ccost=425 #€/kW
tlink_ccost=400 #€/(MW*km)
tlink_lt=30 #y
lidis=58 #km, DK1/2 distance
disrate=.07 #discount rate
disr=30 #y, discount rate lifetime
hs=pd.date_range('2018-01-01T00:00Z','2018-01-01T04:00Z', freq='H')

#Annuity
def annuity(n,r):
    """Calculate the annuity factor for an asset with lifetime n years and
    discount rate of r, e.g. annuity(20,0.05)*20 = 1.6"""
    if r > 0:
        return r/(1. - 1./(1.+r)**n)
    else:
        return 1/n

#DataFrames
dcs=[]
dcs.append(pd.Series(dk_cf[0], index=hs))
dcs.append(pd.Series(dk_cf[1], index=hs))
dms=[]
dms.append(pd.Series(dk_dem[0]*1e3, index=hs))
dms.append(pd.Series(dk_dem[1]*1e3, index=hs))

#code

def run_node(i=1,etype="wind",ccost=osw_ccost):
    print("Simulating unconnected node: "+etype+" ...")
    network = pypsa.Network()
    network.set_snapshots(hs)
    network.add("Carrier", etype)
    network.add("Bus","DK-"+str(i))
    network.add("Generator",
        etype,
        bus="DK-"+str(i),
        carrier=etype,
        capital_cost=ccost*1e3*annuity(30, disrate)*5/8760,
        marginal_cost = 0,
        p_nom_extendable=True,
        p_max_pu=dcs[i-1])
    network.add("Load", "Dem-DK-"+str(i), bus="DK-"+str(i), p_set=dms[i-1])
    network.optimize(solver_name='gurobi')
    print("Cost: "+str(network.objective/network.loads_t.p.sum().sum())+" eur/MWh")
    print("Optimal capacity"+str(network.generators.p_nom_opt)+" MW")

run_node(1,"wind",osw_ccost)
run_node(2,"solar",pvs_ccost)

rb=True
n=0
if(rb):
    print("Simulating connected nodes ...")
    network = pypsa.Network()
    network.set_snapshots(hs)
    network.add("Carrier", "wind")
    network.add("Carrier", "solar")
    
    network.add("Bus","DK-1")
    network.add("Bus","DK-2")
    network.add("Generator",
        "wind",
        bus="DK-1",
        carrier="wind",
        capital_cost=osw_ccost*1e3*annuity(disr, disrate)*5/8760,
        marginal_cost = 0,
        p_nom_extendable=True,
        p_max_pu=dcs[0])

    network.add("Generator",
        "solar",
        bus="DK-2",
        carrier="solar",
        capital_cost=pvs_ccost*1e3*annuity(disr, .07)*5/8760,
        marginal_cost = 0,
        p_nom_extendable=True,
        p_max_pu=dcs[1])
    
    network.add("Load", "Dem-DK-1", bus="DK-1", p_set=dms[0])
    network.add("Load", "Dem-DK-2", bus="DK-2", p_set=dms[1])
    #print(network.loads_t.p_set)
    network.add("Link",
        "DK-link",
        bus0="DK-1",
        bus1="DK-2",
        lifetime=tlink_lt,
        p_nom_extendable=True,
        capital_cost=tlink_ccost*lidis*annuity(disr, disrate)*5/8760,
        efficiency = 1,
        marginal_cost = 0,
        p_min_pu=-1)
    network.optimize(solver_name='gurobi')
    n=network
    print("Cost: "+str(network.objective/network.loads_t.p.sum().sum())+" eur/MWh")
    print("Optimal capacity"+str(network.generators.p_nom_opt)+" MW")
    #print(network.objective)
#wanted: optimal wind/solar capacity, link capacity, average electricity price