#%%
# Modules
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import json

import netex_paths

#%%
stop_columns = ['stop_code', 'name', 'short_name', 'x', 'y', 'gebied']
    # Load the shapefile
flevoland_gemeenten = ['Dronten', 'Urk', 'Noordoostpolder', 'Zeewolde'] 
# Lelystad
    
gdf_gemeenten = gpd.read_file(netex_paths.gemeenten_shapefile)
gdf_flex = gdf_gemeenten[gdf_gemeenten['Gemeentena'].isin(flevoland_gemeenten)].copy()
gdf_flex.plot()
gdf_flex_wgs = gdf_flex.to_crs(epsg=4326)

def get_flex_area_coordinates(gdf):
    flex_union = gdf.union_all()
    a = list(flex_union.exterior.coords)
    c = [str(b[0])+ ' '+str(b[1]) for b in a]
    d = ' '.join(c)
    return d
area_dict = {'flevoland': get_flex_area_coordinates(gdf_flex_wgs)}

with open('flex_area.json', 'w') as f:
    json.dump(area_dict, f)


#%%
# Hubs
df_hubs = pd.read_csv("hubs.csv", sep=';', encoding='latin-1', dtype=str)
df_hubs['stopplacecode'] = 'NL:S:' + df_hubs['stop_code']
df_chb_stopplaces = pd.read_csv(netex_paths.CHB_stopplaces, sep=';', encoding='latin-1', dtype=str,
                                    usecols=['stopplacecode', 'stopplacename', 'rd-x', 'rd-y'])
df_chb_stopplaces = df_chb_stopplaces.rename(columns={'stopplacename':'name'})
df_hubs = df_hubs.merge(df_chb_stopplaces, on='stopplacecode', how='left')
df_hubs['short_name'] = df_hubs['name'].str.replace(' ', '_')
df_hubs['gebied'] = 'hubs'

gdf_hubs = gpd.GeoDataFrame(df_hubs, geometry=gpd.points_from_xy(df_hubs['rd-x'], df_hubs['rd-y']))
gdf_hubs = gdf_hubs.set_crs(epsg=28992).to_crs(epsg=4326)
gdf_hubs['x'] = gdf_hubs['geometry'].x
gdf_hubs['y'] = gdf_hubs['geometry'].y
#%%
# Visualize the results
fig, ax = plt.subplots(figsize=(10, 10))
gdf_flex.to_crs(epsg=4326).plot(ax=ax, color='lightgrey', edgecolor='black', linewidth=1, label='gdf_flex')
gdf_hubs.plot(ax=ax, color='blue', markersize=5, alpha=0.7, label='gdf_stops_hubs')
ax.set_title('Flex-stops')
ax.legend()
ax.set_axis_off()
plt.savefig('flex_stops.png', dpi=300)
plt.show()

#%%
df_stops = pd.concat([gdf_hubs[stop_columns]], ignore_index=True)
df_stops.to_csv(r"hubs_FlexRRReisFlevoland.csv", index=False)
# %%
