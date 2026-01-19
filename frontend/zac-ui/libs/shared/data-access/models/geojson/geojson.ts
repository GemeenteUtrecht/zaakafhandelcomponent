/**
 * A GeoJSON object represents a Geometry, Feature, or collection of
 * Features.
 *
 * o  A GeoJSON object is a JSON object.
 *
 * o  A GeoJSON object has a member with the name "type".  The value of
 *    the member MUST be one of the GeoJSON types.
 *
 * o  A GeoJSON object MAY have a "bbox" member, the value of which MUST
 *    be a bounding box array (see Section 5).
 *
 * o  A GeoJSON object MAY have other members (see Section 6).
 *
 * @see {@link https://datatracker.ietf.org/doc/html/rfc7946#section-3|rfc7946}
 */
export interface GeoJSONObject {
  type: 'Feature' | 'FeatureCollection' | 'Point' | 'MultiPoint' | 'LineString' | 'MultiLineString' | 'Polygon' | 'MultiPolygon' | 'GeometryCollection',
  bbox?: BoundingBox,

  [key: string]: any,
}

/**
 * A GeoJSON object MAY have a member named "bbox" to include
 * information on the coordinate range for its Geometries, Features, or
 * FeatureCollections.  The value of the bbox member MUST be an array of
 * length 2*n where n is the number of dimensions represented in the
 * contained geometries, with all axes of the most southwesterly point
 * followed by all axes of the more northeasterly point.  The axes order
 * of a bbox follows the axes order of geometries.
 *
 * @see {@link https://datatracker.ietf.org/doc/html/rfc7946#section-5|rfc7946}
 */
export interface BoundingBox {
  [key: number]: number,

  length: 4 | 6,
}

/**
 * A Geometry object represents points, curves, and surfaces in
 * coordinate space.  Every Geometry object is a GeoJSON object no
 * matter where it occurs in a GeoJSON text.
 *
 * @see {@link https://datatracker.ietf.org/doc/html/rfc7946#section-3.1|rfc7946}
 */
export interface Geometry extends GeoJSONObject {
  type: 'Point' | 'MultiPoint' | 'LineString' | 'MultiLineString' | 'Polygon' | 'MultiPolygon' | 'GeometryCollection'
  coordinates?: Position | Position[] | Position[][] | Position[][][],
  geometries?: Geometry[]
}

/**
 * For type "Point", the "coordinates" member is a single position.
 *
 * @see {@link https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.2|rfc7946}
 */
export interface Point extends Geometry {
  type: 'Point',
  coordinates: Position
}

/**
 * For type "MultiPoint", the "coordinates" member is an array of
 * positions.
 *
 * @see {@link https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.3|rfc7946}
 */
export interface MultiPoint extends Geometry {
  type: 'MultiPoint',
  coordinates: Position[],
}

/**
 * For type "LineString", the "coordinates" member is an array of two or
 * more positions.
 *
 * @see {@link https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.4|rfc7946}
 */
export interface LineString extends Geometry {
  type: 'LineString',
  coordinates: Position[],
}

/**
 * For type "MultiLineString", the "coordinates" member is an array of
 * LineString coordinate arrays.
 *
 * @see {@link https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.5|rfc7946}
 */
export interface MultiLineString extends Geometry {
  type: 'MultiLineString',
  coordinates: Position[][],
}

/**
 * To specify a constraint specific to Polygons, it is useful to
 * introduce the concept of a linear ring:
 *
 * o  A linear ring is a closed LineString with four or more positions.
 *
 * o  The first and last positions are equivalent, and they MUST contain
 *    identical values; their representation SHOULD also be identical.
 *
 * o  A linear ring is the boundary of a surface or the boundary of a
 *    hole in a surface.
 *
 * o  A linear ring MUST follow the right-hand rule with respect to the
 *    area it bounds, i.e., exterior rings are counterclockwise, and
 *    holes are clockwise.
 *
 * Note: the [GJ2008] specification did not discuss linear ring winding
 * order.  For backwards compatibility, parsers SHOULD NOT reject
 * Polygons that do not follow the right-hand rule.
 *
 * Though a linear ring is not explicitly represented as a GeoJSON
 * geometry type, it leads to a canonical formulation of the Polygon
 * geometry type definition as follows:
 *
 * o  For type "Polygon", the "coordinates" member MUST be an array of
 *    linear ring coordinate arrays.
 *
 * o  For Polygons with more than one of these rings, the first MUST be
 *    the exterior ring, and any others MUST be interior rings.  The
 *    exterior ring bounds the surface, and the interior rings (if
 *    present) bound holes within the surface.
 *
 * @see {@link https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.6|rfc7946}
 */
export interface Polygon extends Geometry {
  type: 'Polygon',
  coordinates: Position[][],
}

/**
 * For type "MultiPolygon", the "coordinates" member is an array of
 * Polygon coordinate arrays.
 *
 * @see {@link https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.7|rfc7946}
 */
export interface MultiPolygon extends Geometry {
  type: 'MultiPolygon',
  coordinates: Position[][][],
}

/**
 * A GeoJSON object with type "GeometryCollection" is a Geometry object.
 * A GeometryCollection has a member with the name "geometries".  The
 * value of "geometries" is an array.  Each element of this array is a
 * GeoJSON Geometry object.  It is possible for this array to be empty.
 *
 * @see {@link https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.8|rfc7946}
 */
export interface GeometryCollection extends Geometry {
  type: 'GeometryCollection',
  geometries: Geometry[],
}

/**
 * A position is the fundamental geometry construct.  The "coordinates"
 * member of a Geometry object is composed of either:
 *
 * o  one position in the case of a Point geometry,
 *
 * o  an array of positions in the case of a LineString or MultiPoint
 *    geometry,
 *
 * o  an array of LineString or linear ring (see Section 3.1.6)
 *    coordinates in the case of a Polygon or MultiLineString geometry,
 *    or
 *
 * o  an array of Polygon coordinates in the case of a MultiPolygon
 *    geometry.
 *
 * A position is an array of numbers.  There MUST be two or more
 * elements.  The first two elements are longitude and latitude, or
 * easting and northing, precisely in that order and using decimal
 * numbers.  Altitude or elevation MAY be included as an optional third
 * element.
 *
 * Implementations SHOULD NOT extend positions beyond three elements
 * because the semantics of extra elements are unspecified and
 * ambiguous.  Historically, some implementations have used a fourth
 * element to carry a linear referencing measure (sometimes denoted as
 * "M") or a numerical timestamp, but in most situations a parser will
 * not be able to properly interpret these values.  The interpretation
 * and meaning of additional elements is beyond the scope of this
 * specification, and additional elements MAY be ignored by parsers.
 *
 * @see {@link foo|rfc7946}
 */
export interface Position {
  [index: number]: number,

  length: 2 | 3
}

/**
 * A Feature object represents a spatially bounded thing.  Every Feature
 * object is a GeoJSON object no matter where it occurs in a GeoJSON
 * text.
 *
 * @see {@link https://datatracker.ietf.org/doc/html/rfc7946#section-3.2|rfc7946}
 */
export interface Feature extends GeoJSONObject {
  type: 'Feature',
  geometry: Geometry | null,
  properties: Properties
}

/**
 * A GeoJSON object with the type "FeatureCollection" is a
 * FeatureCollection object.  A FeatureCollection object has a member
 * with the name "features".  The value of "features" is a JSON array.
 * Each element of the array is a Feature object as defined above.  It
 * is possible for this array to be empty.
 *
 * @see {@link https://datatracker.ietf.org/doc/html/rfc7946#section-3.3|rfc7946}
 */
export interface FeatureCollection extends GeoJSONObject {
  type: 'FeatureCollection',
  features: Feature[],
}

/**
 * A Feature object has a member with the name "properties".  The
 * value of the properties member is an object (any JSON object or a
 * JSON null value).
 *
 * @see {@link https://datatracker.ietf.org/doc/html/rfc7946#section-3.2|rfc7946}
 */
export interface Properties {
  [key: string]: any
}
