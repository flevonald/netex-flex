#%%
# Modules
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from generate_netex_from_csv import read_config
import paths


#%% alle haltes

project = 'FlexRRReis_RH'
config = read_config(f'config_{project}.csv')
gemeentecodes = config['gemeentecodes'].split(', ')

#%%
df_chb_quays = pd.read_csv(Path(paths.CHB) / 'CHB_quays.csv', sep=';', encoding='latin-1', dtype=str)
df_chb_quays = df_chb_quays.loc[df_chb_quays['quaymunicipality'].isin(gemeentecodes)]

#%%

df_chb_stopplaces = pd.read_csv(Path(paths.CHB)/ 'CHB_stopplaces.csv', sep=';', encoding='latin-1', dtype=str,
                                    usecols=['stopplacecode', 'stopplacename', 'rd-x', 'rd-y'])
#%%
df_haltes = df_chb_stopplaces.loc[df_chb_stopplaces['stopplacecode'].isin(df_chb_quays['stopplacecode']), ['stopplacecode','stopplacename','rd-x','rd-y']].copy()
df_haltes['code'] = df_haltes['stopplacecode'].str.strip('NL:S:')
df_haltes = df_haltes.rename(columns={'stopplacename':'name'})
df_haltes['short_name'] = df_haltes['name'].str.replace(' ', '_')
df_haltes['gebied'] = config['zone_name']
df_haltes['halte'] = True

#%%
try:
    df_hubs = pd.read_csv(f"hubs_{project}.csv", sep=',', encoding='latin-1', dtype=str)
    df_hubs['stopplacecode'] = 'NL:S:' + df_hubs['code']
    df_hubs['short_name'] = df_hubs['name'].str.replace(' ', '_')
    df_hubs['gebied'] = 'hubs'
    df_hubs['halte'] = True
    df_hubs = df_hubs.merge(df_chb_stopplaces, on='stopplacecode', how='left')

except FileNotFoundError:
    df_hubs = pd.DataFrame(columns=['stopplacecode','name','rd-x','rd-y','code','short_name','gebied','halte'])
    print(f"No hubs file found for project {project}. Proceeding without hubs.")

df_stops = pd.DataFrame(columns=['code','name','short_name','gebied','rd-x','rd-y', 'halte'])
for df in [df_haltes, df_hubs]:
    if not df.empty:
        df_stops = pd.concat([df_stops, df], ignore_index=True)


gdf_stops = gpd.GeoDataFrame(df_stops, geometry=gpd.points_from_xy(df_stops['rd-x'], df_stops['rd-y']))
gdf_stops = gdf_stops.set_crs(epsg=28992).to_crs(epsg=4326)
gdf_stops['x'] = gdf_stops['geometry'].x
gdf_stops['y'] = gdf_stops['geometry'].y

stop_columns = ['code','name','short_name','gebied','x','y', 'halte']
df_stops = gdf_stops[stop_columns]
df_stops.to_csv(f"stops_{project}.csv", index=False, sep=';', encoding='utf-8-sig')
# %%
