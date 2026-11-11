"""Use an indexed PostGIS prefilter when available; retain exact deterministic filtering."""
from sqlalchemy import text

def candidates(db,query,lat,lng,radius):
    if db.bind.dialect.name=='postgresql':
        schema=db.scalar(text("select n.nspname from pg_extension e join pg_namespace n on n.oid=e.extnamespace where e.extname='postgis'"))
        if schema in ('extensions','public'):
            # Schema is allowlisted; all location values remain bound parameters.
            clause=f'{schema}.st_dwithin({schema}.st_setsrid({schema}.st_makepoint(restaurants.longitude,restaurants.latitude),4326)::{schema}.geography,{schema}.st_setsrid({schema}.st_makepoint(:geo_lng,:geo_lat),4326)::{schema}.geography,:geo_radius,false)'
            return query.where(text(clause)).params(geo_lng=lng,geo_lat=lat,geo_radius=radius*1010)
    # Cheap SQL bounding box also reduces work on SQLite or without the extension.
    from .database import Restaurant
    import math
    delta_lat=radius/110.0;delta_lng=radius/(110.0*math.cos(math.radians(lat)))
    return query.where(Restaurant.latitude.between(lat-delta_lat,lat+delta_lat),Restaurant.longitude.between(lng-delta_lng,lng+delta_lng))
