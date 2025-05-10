# app/utils.py

import os
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import folium
from folium import plugins
from app import app

ALLOWED_EXTENSIONS = {'tif', 'tiff'}

def is_allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_orthophotos(files, session_id):
    output_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    map_path = os.path.join(output_dir, 'map.html')
    
    m = None
    
    for file in files:
        with rasterio.open(file) as src:
            dst_crs = 'EPSG:4326'
            transform, width, height = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds)
            kwargs = src.meta.copy()
            kwargs.update({'crs': dst_crs, 'transform': transform, 'width': width, 'height': height})

            # Réprojection dans un tableau en mémoire
            destination = np.zeros((src.count, height, width), dtype=src.dtypes[0])
            for i in range(1, src.count + 1):
                reproject(
                    source=src.read(i),
                    destination=destination[i-1],
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest
                )

            # Construction de l'image RGB (3 premières bandes)
            img = np.dstack([destination[i] for i in range(min(3, src.count))])

            # Détermination des limites géographiques
            left, bottom = transform * (0, height)
            right, top = transform * (width, 0)

            # Initialisation de la carte
            if m is None:
                center = [(top + bottom) / 2, (left + right) / 2]
                m = folium.Map(location=center, zoom_start=12, tiles=None)
                # Ajout du fond Google Satellite
                folium.TileLayer(
                    tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                    attr='Google Satellite',
                    name='Google Satellite',
                    overlay=False,
                    control=True
                ).add_to(m)
                
                # Ajout d'autres fonds de carte
                folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(m)
                folium.TileLayer(
                    tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
                    attr='Google Maps',
                    name='Google Maps',
                    overlay=False,
                    control=True
                ).add_to(m)

            # Superposition de l'orthophoto
            folium.raster_layers.ImageOverlay(
                image=img,
                bounds=[[bottom, left], [top, right]],
                opacity=0.6,
                name=os.path.basename(file)
            ).add_to(m)

    # Ajout des contrôles de couches
    folium.LayerControl().add_to(m)
    
    # Ajout du contrôle de dessin
    plugins.Draw(
        export=True,
        position='topleft',
        draw_options={
            'polyline': True,
            'polygon': True,
            'rectangle': True,
            'circle': True,
            'marker': True,
            'circlemarker': False
        }
    ).add_to(m)
    
    # Ajout de la mesure
    plugins.MeasureControl(
        position='bottomleft',
        primary_length_unit='meters',
        secondary_length_unit='kilometers',
        primary_area_unit='sqmeters',
        secondary_area_unit='hectares'
    ).add_to(m)

    # Sauvegarde de la carte
    m.save(map_path)
    
    return map_path