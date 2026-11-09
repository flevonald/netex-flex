#%%
# Modules
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import json

import paths

#%%
project = "FlexRRReisFlevoland"

stop_columns = ['stop_code', 'name', 'short_name', 'x', 'y', 'gebied']
    # Load the shapefile
flevoland_gemeenten = ['Lelystad', 'Dronten', 'Urk', 'Noordoostpolder', 'Zeewolde'] 
# Lelystad
    
gdf_gemeenten = gpd.read_file(paths.gemeenten_shapefile)
gdf_flex = gdf_gemeenten[gdf_gemeenten['Gemeentena'].isin(flevoland_gemeenten)].copy()
gdf_flex.plot()
gdf_flex_wgs = gdf_flex.to_crs(epsg=4326)

def get_flex_area_coordinates(gdf):
    flex_union = gdf.union_all()
    a = list(flex_union.exterior.coords)
    c = [str(b[1])+ ' '+str(b[0]) for b in a]
    d = ' '.join(c)
    return d
area_dict = {'flevoland': get_flex_area_coordinates(gdf_flex_wgs)}

with open(f'flex_area_{project}.json', 'w') as f:
    json.dump(area_dict, f)


#%%

#%%
# Visualize the results
fig, ax = plt.subplots(figsize=(10, 10))
gdf_flex.to_crs(epsg=4326).plot(ax=ax, color='lightgrey', edgecolor='black', linewidth=1, label='gdf_flex')
gdf_hubs = gpd.GeoDataFrame(hubs, geometry=gpd.points_from_xy(hubs['x'], hubs['y']))
gdf_hubs = gdf_hubs.set_crs(epsg=4326)
gdf_hubs.plot(ax=ax, color='blue', markersize=5, alpha=0.7, label='gdf_stops_hubs')
ax.set_title('Flex-stops')
ax.legend()
ax.set_axis_off()
plt.savefig('flex_stops.png', dpi=300)
plt.show()

#%%
df_stops = pd.concat([gdf_hubs[stop_columns]], ignore_index=True)
df_stops.to_csv(r"stops_FlexRRReisFlevoland.csv", index=False)
# %%
