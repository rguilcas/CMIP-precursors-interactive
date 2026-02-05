import hvplot.pandas
import numpy as np
import pandas as pd
import panel as pn
import xarray as xr
import geopandas as gpd
import cartopy.crs as ccrs
from bokeh.models import HoverTool
import holoviews as hv
from holoviews import streams

pn.extension(design="material", sizing_mode="stretch_width")

@pn.cache
def get_data():
    ds1= xr.open_dataset("data/LENS_precomputed_terms_combined.nc")
    gdf_regions = gpd.read_file('data/rainfall_regions.geojson')
    ds1 = ds1.assign_coords(region_id = gdf_regions.index)
    ds1 = xr.concat([ds1,ds1.sum('source').assign_coords(source='all')], dim='source') 
    
    # gdf_regions.index = [K39_regions[k] for k in gdf_regions.index]
    

    return ds1, gdf_regions

ds1, gdf_regions = get_data()
# data.tail()


def get_plot(model='CESM2', season='DJF', term='bias', source='dyn', vmax=50):
    """Plots the rolling average and the outliers"""
    ds_sel = (
        ds1
        .sel(model=model, season=season, term=term, source=source)
        .sum("synoptic_bin") / 0.05 * 100
    )

    gdf = gdf_regions.copy()
    gdf[term] = ds_sel.individual_term.to_series()
    
    # hover = HoverTool(tooltips=tooltips)
    hover = HoverTool(tooltips = [('@index', '@term')])
    poly_plot = gdf.hvplot.polygons( crs=ccrs.PlateCarree(), color=term)\
        .opts(height=800, 
              width=800, 
              # tools=['hover'],
              tools=['tap', 'hover'],  # Ensure tap is here
              # selection_mode='single',   # Or 'multiple'
              cmap = 'RdBu',
              color=term, 
              colorbar=True, 
              clim=(-vmax, vmax),
              projection=ccrs.PlateCarree(),
              axiswise=False, 
              shared_axes=True
             )#+gv.feature.ocean
    selection = streams.Selection1D(source=poly_plot)
    @pn.depends(selection.param.index)
    def update_secondary_plot(index):
        if not index:
            return "### Please select a region"
        # print(index)
        regions = gdf.iloc[index].index
        region_names='  \n'+'  \n'.join(regions)
        # data=gdf.loc[index].index
        ds_sel_barplot = (
                ds1
                .sel(model=model, season=season, term=term,  region_id=regions)
                .sum("synoptic_bin") / 0.05 * 100
            ).individual_term
        series =  ds_sel_barplot.to_series()#
        series.index = series.index.reorder_levels([1,0])
        bars = series.hvplot.bar(title=term)
        return bars.opts(height=800, 
                         width=200)*hv.HLine(0).opts(color='k')#f"### You clicked on:  \n{region_names}"

    
    layout = pn.Row(poly_plot, update_secondary_plot)
    return layout

model_widget = pn.widgets.RadioButtonGroup(
    description="Model selection",
    name="Model",
    options=list(ds1.model.values),
)
season_widget = pn.widgets.RadioButtonGroup(
    description="Season selection",
    name="Season",
    options=list(ds1.season.values),
)
term_widget = pn.widgets.RadioButtonGroup(
    description="Term selection",
    name="Term",
    options=['bias','trend'],
)
source_widget = pn.widgets.RadioButtonGroup(
    description="Source selection",
    name="Source",
    options=list(ds1.source.values),
)
vmax_widget = pn.widgets.IntSlider(name="Colormap max value", value=50, start=1, end=150)

bound_plot = pn.bind(
    get_plot, model=model_widget, season=season_widget, term=term_widget, source=source_widget, vmax=vmax_widget
)

app = pn.template.MaterialTemplate(
    site="Panel",
    title="CMIP European rainfall decomposition",
    sidebar=[term_widget, source_widget, season_widget,model_widget, vmax_widget],
    main=[bound_plot],
)

app.servable()