try:
    from osgeo import osr
except ImportError:
    import osr


class CoordinateTransformer:
    def __init__(self, source_wkt, target_epsg=4326):
        """
        Initialize the transformer with source WKT and target EPSG.

        :param source_wkt: WKT of the source projection.
        :param target_epsg: EPSG code of the target projection (default: WGS84).
        """
        self.source_proj = osr.SpatialReference()
        self.source_proj.ImportFromWkt(source_wkt)

        self.target_proj = osr.SpatialReference()
        self.target_proj.SetWellKnownGeogCS(f"EPSG:{target_epsg}")

        self.transformer = osr.CoordinateTransformation(self.source_proj, self.target_proj)

    def unproject(self, point):
        """
        Convert a point from the source projection to the target projection.

        :param point: A tuple of (x, y) coordinates in the source projection.
        :return: A tuple of (longitude, latitude) in the target projection.
        """
        projected = self.transformer.TransformPoint(point[0], point[1])
        return (projected[0], projected[1])

    def destroy(self):
        """
        Clean up the resources used by the transformer.
        """
        del self.transformer
        del self.source_proj
        del self.target_proj