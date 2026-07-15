#%%
# Modules
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

import paths

#%%
stop_columns = ['code', 'name', 'short_name', 'x', 'y', 'gebied']
    # Load the shapefile
flevoland_gemeenten = ['Lelystad', 'Dronten'] 
# ,'Noordoostpolder','Urk', 'Zeewolde'
    
gdf_gemeenten = gpd.read_file(paths.gemeenten_shapefile)
gdf_flex = gdf_gemeenten[gdf_gemeenten['Gemeentena'].isin(flevoland_gemeenten)].copy()
gdf_flex.plot()
gdf_flex_wgs = gdf_flex.to_crs(epsg=4326)

#%%
bag_file = Path(paths.bag_light)

gdf_stops_bag = gpd.read_file(bag_file, layer='verblijfsobject', bbox=gdf_flex)
gdf_stops_bag = gdf_stops_bag.loc[gdf_stops_bag['woonplaats_naam'].isin(flevoland_gemeenten)].head(500)
gdf_stops_bag['geometry'] = gdf_stops_bag['geometry'].centroid
gdf_stops_bag = gdf_stops_bag.to_crs(epsg=4326)

#%%

gdf_stops_bag['x'] = gdf_stops_bag['geometry'].x
gdf_stops_bag['y'] = gdf_stops_bag['geometry'].y
gdf_stops_bag['index'] = gdf_stops_bag.index
gdf_stops_bag['stop_code'] = 'PFL_Adress' + gdf_stops_bag['index'].astype(str)
gdf_stops_bag['name'] = gdf_stops_bag['openbare_ruimte_naam'] + ' ' + gdf_stops_bag['huisnummer'].astype(str) + ' ' + gdf_stops_bag['woonplaats_naam']
gdf_stops_bag['short_name'] = gdf_stops_bag['name'].str.replace(' ', '_')
gdf_stops_bag['gebied'] = 'Flevoland'


#%%
# Hubs
df_hubs = pd.read_csv("hubs.csv", sep=';', encoding='latin-1', dtype=str)
df_hubs['stopplacecode'] = 'NL:S:' + df_hubs['stop_code']
df_chb_stopplaces = pd.read_csv(paths.CHB / 'CHB_stopplaces.csv', sep=';', encoding='latin-1', dtype=str,
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
gdf_stops_bag.plot(ax=ax, color='red', markersize=5, alpha=0.7, label='gdf_stops_bag')
gdf_hubs.plot(ax=ax, color='blue', markersize=5, alpha=0.7, label='gdf_stops_hubs')
ax.set_title('Flex-stops')
ax.legend()
ax.set_axis_off()
plt.savefig('flex_stops.png', dpi=300)
plt.show()

#%%
df_adresses = pd.concat([gdf_stops_bag[stop_columns], gdf_hubs[stop_columns]], ignore_index=True)
df_adresses.to_csv(r"adresses_FlexRRReisFlevoland.csv", index=False)
# %%
