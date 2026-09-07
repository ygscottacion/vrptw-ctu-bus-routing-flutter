import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';

/// Service tích hợp OSRM (Open Source Routing Machine)
/// để lấy tọa độ đường đi thực tế theo mạng lưới giao thông đường bộ.
class RoutingService {
  RoutingService._();
  static final RoutingService _instance = RoutingService._();
  factory RoutingService() => _instance;

  final Map<String, List<LatLng>> _cache = {};

  /// Lấy danh sách điểm tọa độ uốn lượn theo đúng tuyến đường giao thông
  Future<List<LatLng>> getDrivingRoute(List<LatLng> waypoints) async {
    if (waypoints.length < 2) return waypoints;

    // Cache key dựa trên các tọa độ
    final key = waypoints
        .map((w) => '${w.latitude.toStringAsFixed(4)},${w.longitude.toStringAsFixed(4)}')
        .join(';');

    if (_cache.containsKey(key)) {
      return _cache[key]!;
    }

    try {
      // Format OSRM: lng,lat;lng,lat...
      final coordsStr = waypoints
          .map((w) => '${w.longitude},${w.latitude}')
          .join(';');

      final url = Uri.parse(
        'https://router.project-osrm.org/route/v1/driving/$coordsStr?overview=full&geometries=geojson',
      );

      final response = await http
          .get(url, headers: {'User-Agent': 'CTU-Bus-Routing/1.0'})
          .timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        if (data['code'] == 'Ok' &&
            data['routes'] is List &&
            (data['routes'] as List).isNotEmpty) {
          final route = data['routes'][0] as Map<String, dynamic>;
          final geometry = route['geometry'] as Map<String, dynamic>?;
          if (geometry != null && geometry['coordinates'] is List) {
            final rawCoords = geometry['coordinates'] as List<dynamic>;
            final points = rawCoords.map<LatLng>((pt) {
              final list = pt as List<dynamic>;
              final lng = (list[0] as num).toDouble();
              final lat = (list[1] as num).toDouble();
              return LatLng(lat, lng);
            }).toList();

            if (points.isNotEmpty) {
              _cache[key] = points;
              return points;
            }
          }
        }
      }
    } catch (_) {
      // Fallback sang đường thẳng nếu mạng lỗi hoặc timeout
    }

    return waypoints;
  }
}
