// SOUL Maps on the device (docs/11-MAPS.md): what the cloud sends and how SOUL
// draws it and walks it, with no GPS and no compass.
//
//   MapBundle   the "SMB1" vector bundle (ai/suflet_ai/maps.py encode_bundle):
//               water, parks, roads by rank, rail, place names, in whole
//               pixels of a 960 x 960 area at zoom z (Web Mercator). A few KB.
//   MapView     where the 480 px disc looks: a centre in world pixels and a
//               zoom (whole levels + a 1..2 scale while pinch-free zooming on
//               the rim), north up. world <-> screen.
//   RouteData   a route (polyline5 shape + maneuvers) as the cloud planned it.
//   NavState    progress along it from the fixes SOUL gets (the owner's phone,
//               Wi-Fi), or by hand ("next step"): the current step, metres to
//               the turn, the turn's angle RELATIVE TO THE ROUTE (there is no
//               compass, so the arrow means "walk along the line, then turn
//               this way"), off-route, arrived, ETA.
//   MapPainter  draws a bundle (+ route, + you) into an RGB565 canvas: AA
//               polylines with a width, scanline-filled polygons, the dark
//               glass palette; into a cached layer so the eyes' repairs only
//               blit it.
//
// Transport-free and tested on the PC (test/test_suflet/test_apps.cpp).
#pragma once
#include <stddef.h>
#include <stdint.h>

#include <string>
#include <vector>

#include "Canvas.h"
#include "Color.h"

namespace suflet {
namespace maps {

// device classes (the same numbers as maps.py)
enum Cls : uint8_t { Water = 1, Park, RoadMajor, RoadMid, RoadMinor, Path, Rail, Building, Place, Poi };
enum Kind : uint8_t { Line = 1, Poly = 2, Point = 3 };

constexpr int kTile = 256;
constexpr int kMinZ = 3, kMaxZ = 18;

// Web Mercator, double precision (world pixels at zoom 18 reach 67 million)
void worldPx(double lat, double lon, int z, double& x, double& y);
void latLon(double x, double y, int z, double& lat, double& lon);
double haversine(double lat1, double lon1, double lat2, double lon2);  // metres
double bearing(double lat1, double lon1, double lat2, double lon2);    // degrees, 0 = north, clockwise
// metres per pixel at a latitude and zoom
double metresPerPx(double lat, int z);

// Google's encoded polyline (precision 5); false on a malformed string
bool decodePolyline(const char* s, std::vector<double>& latlon, int precision = 5);

struct Feature {
  uint8_t cls = 0, kind = 0;
  uint32_t first = 0;   // index into MapBundle::pts (pairs)
  uint16_t count = 0;   // points
  uint16_t label = 0;   // offset into MapBundle::labels (points only)
  uint8_t labelLen = 0;
};

struct MapBundle {
  uint8_t z = 0;
  uint32_t ox = 0, oy = 0;  // world pixel of the bundle's top-left at zoom z
  uint16_t w = 0, h = 0;
  std::vector<Feature> feats;
  std::vector<int16_t> pts;  // x0 y0 x1 y1 ...
  std::string labels;
  // false on anything malformed (size, magic, counts, truncated varints): the bundle is left empty
  bool decode(const uint8_t* data, size_t n);
  bool empty() const { return feats.empty(); }
  void clear();
  std::string labelOf(const Feature& f) const { return labels.substr(f.label, f.labelLen); }
  // does the bundle cover the world rectangle (zoom z) [x0,x1)x[y0,y1)?
  bool covers(int z, double x0, double y0, double x1, double y1) const;
  size_t bytes() const { return pts.size() * 2 + feats.size() * sizeof(Feature) + labels.size(); }
};

struct MapView {
  int z = 16;          // whole zoom level of the data asked for
  float scale = 1.0f;  // 1..2: between levels while zooming on the rim
  double cx = 0, cy = 0;  // centre, world px at zoom z
  int screenW = 480, screenH = 480;
  void centerOn(double lat, double lon);
  void toScreen(double wx, double wy, float& sx, float& sy) const;  // world px (zoom z) -> screen px
  void toWorld(float sx, float sy, double& wx, double& wy) const;
  void pan(float dxScreen, float dyScreen);  // drag: the map follows the finger
  // zoom by a factor around the screen centre; whole levels carry over into z (clamped to kMinZ..kMaxZ)
  void zoomBy(float factor);
  double lat() const;
  double lon() const;
};

// ------------------------------------------------------------------ routes --

enum class Turn : uint8_t { Depart, Straight, SlightLeft, Left, SharpLeft, SlightRight, Right, SharpRight, UTurn,
                            Roundabout, Arrive, Ferry };
const char* turnWord(Turn t, bool ro);

struct Step {
  Turn turn = Turn::Straight;
  int distM = 0;      // from this maneuver to the next
  int idx = 0;        // shape point of the maneuver
  std::string street;
  int exit = 0;
};

struct RouteData {
  std::string id, to, mode = "walk", src;
  int distM = 0, durS = 0;
  double destLat = 0, destLon = 0;
  std::vector<double> shape;  // lat lon lat lon ...
  std::vector<Step> steps;
  std::vector<double> cum;    // metres along the shape at each point
  bool valid() const { return shape.size() >= 4 && !steps.empty(); }
  int points() const { return (int)shape.size() / 2; }
  // {"id","to","mode","dist","dur","shape","steps":[[turn,dist,idx,street,exit]...],"dest":[lat,lon]}
  bool parse(const char* json, size_t n);
  // the turn at step i as an angle relative to the way you walk along the route (degrees, + = right),
  // measured from the shape ~20 m before and after the maneuver
  float turnAngle(int i) const;
};

struct NavFix {
  double lat = 0, lon = 0;
  float accM = 50;
  uint32_t at = 0;  // local epoch
};

class NavState {
 public:
  void start(const RouteData* r, uint32_t now);
  void stop() { route_ = nullptr; }
  bool active() const { return route_ != nullptr; }
  // a new fix (phone / Wi-Fi): snaps it onto the route, moves the current step forward (never back
  // more than one step: a coarse Wi-Fi guess must not undo progress), flags off-route (> 45 m + accuracy)
  void fix(const NavFix& f);
  // by hand: "I'm at the turn" (the next step) / back one
  void next();
  void prev();
  int step() const { return step_; }                 // the maneuver ahead
  float alongM() const { return along_; }            // metres travelled along the route
  float toTurnM() const;                             // metres to the maneuver ahead
  float leftM() const;                               // metres to the destination
  bool offRoute() const { return off_; }
  bool arrived() const { return arrived_; }
  bool hasFix() const { return hasFix_; }
  const NavFix& lastFix() const { return last_; }
  // seconds left at the mode's pace (walk 1.35 m/s, bike 4.2 m/s, car: the route's own average)
  int etaS() const;
  // where on the route (lat/lon) the snapped position is
  void position(double& lat, double& lon) const;

 private:
  const RouteData* route_ = nullptr;
  int step_ = 1;  // steps[0] is "depart": the first maneuver ahead is steps[1]
  float along_ = 0;
  bool off_ = false, arrived_ = false, hasFix_ = false;
  NavFix last_;
};

// --------------------------------------------------------------- painting --

struct MapStyle {
  Rgb land = Rgb::hex(0x0B0C12), water = Rgb::hex(0x14294A), park = Rgb::hex(0x13261E), building = Rgb::hex(0x1A1B24);
  Rgb major = Rgb::hex(0xE9D9B4), mid = Rgb::hex(0xB8AC92), minor = Rgb::hex(0x5E5A55), path = Rgb::hex(0x48443F);
  Rgb rail = Rgb::hex(0x6D6A86), label = Rgb::hex(0xFFF0C8);
  Rgb route = Rgb::hex(0xFFB347), you = Rgb::hex(0x9FC6FF);
};

class MapPainter {
 public:
  MapStyle style;
  // the map (land, polygons, lines, labels) for `v` into `cv` (inside its clip); route/you optional
  void paint(Canvas& cv, const MapBundle& b, const MapView& v, const Font* labelFont);
  void paintRoute(Canvas& cv, const RouteData& r, const MapView& v, int fromPoint, float alpha = 1);
  void paintYou(Canvas& cv, float sx, float sy, float accPx, float t);
  // an anti-aliased line of width `w` (px), blended; clipped to the canvas clip
  static void line(Canvas& cv, float x0, float y0, float x1, float y1, float w, Rgb c, float alpha);
  // an even-odd filled polygon (screen px), 2x vertical supersampling
  void polygon(Canvas& cv, const float* xy, int n, Rgb c, float alpha);
  uint32_t segments = 0, polys = 0;  // statistics of the last paint()

 private:
  std::vector<float> xs_;
  std::vector<float> scratch_;
};

}  // namespace maps
}  // namespace suflet
