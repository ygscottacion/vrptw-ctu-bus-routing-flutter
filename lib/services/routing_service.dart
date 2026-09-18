import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../config/api_config.dart';

/// Service tích hợp Endpoint Nội bộ Backend Goong Polyline
/// để lấy tọa độ đường đi uốn lượn theo đúng mạng lưới giao thông đường bộ.
class RoutingService {
  RoutingService._();
  static final RoutingService _instance = RoutingService._();
  factory RoutingService() => _instance;

  final Map<String, List<LatLng>> _cache = {};

  /// Lấy danh sách điểm tọa độ uốn lượn theo đúng tuyến đường giao thông từ Backend
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
      // Format backend: waypoints=lat1,lng1;lat2,lng2...
      final coordsStr = waypoints
          .map((w) => '${w.latitude},${w.longitude}')
          .join(';');

      final token = Supabase.instance.client.auth.currentSession?.accessToken;
      final url = Uri.parse(
        '${ApiConfig.baseUrl}/routes/polyline?waypoints=$coordsStr',
      );

      final response = await http
          .get(
            url,
            headers: {
              'Content-Type': 'application/json',
              'User-Agent': 'CTU-Bus-Routing/2.0',
              if (token != null) 'Authorization': 'Bearer $token',
            },
          )
          .timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        final pointsRaw = data['points'] as List<dynamic>?;
        if (pointsRaw != null && pointsRaw.isNotEmpty) {
          final points = pointsRaw.map<LatLng>((pt) {
            final list = pt as List<dynamic>;
            final lat = (list[0] as num).toDouble();
            final lng = (list[1] as num).toDouble();
            return LatLng(lat, lng);
          }).toList();

          if (points.isNotEmpty) {
            _cache[key] = points;
            return points;
          }
        }
      }
    } catch (_) {
      // Fallback sang đường thẳng nếu mạng lỗi hoặc timeout
    }

    return waypoints;
  }
}

