import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../features/auth/auth_repository.dart';

import 'package:supabase_flutter/supabase_flutter.dart';

class ApiService {
  ApiService(this._authRepo);

  final AuthRepository _authRepo;

  String? get _authToken => _authRepo.currentAccessToken;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_authToken != null) 'Authorization': 'Bearer $_authToken',
      };

  Future<Map<String, dynamic>?> fetchMe() async {
    if (_authToken == null) return null;
    try {
      final response = await http
          .get(Uri.parse('${ApiConfig.baseUrl}${ApiConfig.authMe}'),
              headers: _headers)
          .timeout(const Duration(seconds: 6));
      if (response.statusCode != 200) return null;
      return json.decode(response.body) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>?> fetchMeDirectSupabase(String uid) async {
    try {
      final res = await Supabase.instance.client
          .from('profiles')
          .select()
          .eq('id', uid)
          .maybeSingle();
      if (res != null) {
        return Map<String, dynamic>.from(res);
      }
    } catch (_) {}
    return null;
  }

  Future<List<dynamic>> fetchLocations() async {
    final url = Uri.parse('${ApiConfig.baseUrl}${ApiConfig.locations}');
    try {
      final response = await http
          .get(url, headers: _headers)
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        return json.decode(response.body) as List<dynamic>;
      }
      return [];
    } catch (_) {
      return [];
    }
  }

  Future<List<dynamic>> fetchVehicles() async {
    final url = Uri.parse('${ApiConfig.baseUrl}${ApiConfig.vehicles}');
    final response = await http.get(url, headers: _headers);
    if (response.statusCode == 200) {
      return json.decode(response.body) as List<dynamic>;
    }
    throw Exception('Khong the tai danh sach xe buyt: ${response.statusCode}');
  }

  Future<List<dynamic>> fetchDriverRoutes(String driverId) async {
    // 1. Thu goi API FastAPI /routes (RBAC da tu filter theo driver)
    try {
      final url = Uri.parse('${ApiConfig.baseUrl}${ApiConfig.routesActive}');
      final response = await http
          .get(url, headers: _headers)
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final list = json.decode(response.body) as List<dynamic>;
        if (list.isNotEmpty) return list;
      }
    } catch (_) {}

    // 2. Fallback query truc tiep tu Supabase DB
    try {
      final actualDriverId =
          driverId.isNotEmpty ? driverId : (_authRepo.currentUser?.id ?? '');
      String? vehicleId;
      if (actualDriverId.isNotEmpty) {
        final vehicleRes = await Supabase.instance.client
            .from('vehicles')
            .select('id')
            .eq('driver_id', actualDriverId)
            .maybeSingle();
        vehicleId = vehicleRes?['id']?.toString();
      }

      final query = Supabase.instance.client
          .from('routes')
          .select('*, route_stops(*, locations(*)), vehicles(*)');

      final routesRes = vehicleId != null
          ? await query
              .eq('vehicle_id', vehicleId)
              .order('service_date', ascending: false)
          : await query.order('service_date', ascending: false).limit(2);

      if ((routesRes as List).isNotEmpty) {
        final routes = (routesRes as List).map((r) {
          final rawStops = (r['route_stops'] as List? ?? [])
            ..sort((a, b) =>
                (a['stop_order'] ?? 0).compareTo(b['stop_order'] ?? 0));
          return {
            ...r,
            'stops': rawStops.map((s) {
              final loc = s['locations'] ?? s['location'] ?? {};
              return {
                'id': s['id'],
                'name': loc['name'] ?? 'Trạm đón',
                'latitude': loc['latitude'],
                'longitude': loc['longitude'],
                'stop_order': s['stop_order'],
                'arrival_time': s['arrival_time'],
              };
            }).toList(),
          };
        }).toList();
        return routes;
      }
    } catch (_) {}

    return [];
  }

  Future<List<dynamic>> fetchActiveRoutes() async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.routesActive}'),
      headers: _headers,
    );
    if (response.statusCode == 200) {
      return json.decode(response.body) as List<dynamic>;
    }
    throw Exception('Khong the tai danh sach tuyen: ${response.statusCode}');
  }

  Future<List<dynamic>> fetchMyTickets() async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.ticketsMe}'),
      headers: _headers,
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    return json.decode(response.body) as List<dynamic>;
  }

  Future<Map<String, dynamic>> bookTicket({
    required String pickupLocationId,
    required DateTime serviceDate,
    required String sessionId,
    required String tripType,
  }) async {
    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.ticketsBuy}'),
      headers: _headers,
      body: json.encode({
        'pickup_location_id': pickupLocationId,
        'service_date': serviceDate.toIso8601String().split('T').first,
        'session_id': sessionId,
        'trip_type': tripType,
      }),
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(_message(response));
    }
    return json.decode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> fetchRouteDetails(String routeId) async {
    try {
      final response = await http
          .get(
            Uri.parse('${ApiConfig.baseUrl}${ApiConfig.routeDetails}$routeId'),
            headers: _headers,
          )
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        return Map<String, dynamic>.from(json.decode(response.body) as Map);
      }
    } catch (_) {}

    try {
      final res = await Supabase.instance.client
          .from('routes')
          .select('*, route_stops(*, locations(*)), vehicles(*)')
          .eq('id', routeId)
          .maybeSingle();
      if (res != null) {
        final rawStops = (res['route_stops'] as List? ?? [])
          ..sort((a, b) =>
              (a['stop_order'] ?? 0).compareTo(b['stop_order'] ?? 0));
        return {
          ...res,
          'stops': rawStops.map((s) {
            final loc = s['locations'] ?? {};
            return {
              'id': s['id'],
              'location': loc,
              'stop_order': s['stop_order'],
              'arrival_time': s['arrival_time'],
            };
          }).toList(),
        };
      }
    } catch (_) {}

    throw Exception('Không tìm thấy thông tin tuyến xe: $routeId');
  }

  Future<Map<String, dynamic>> verifyTicket(String qrCode) =>
      _post(ApiConfig.ticketsVerifyQr, {'qr_code': qrCode});

  Future<Map<String, dynamic>> reportIncident({
    required String title,
    String? description,
    String? vehicleId,
  }) =>
      _post(ApiConfig.incidents, {
        'title': title,
        if (description != null) 'description': description,
        if (vehicleId != null) 'vehicle_id': vehicleId,
      });

  Future<Map<String, dynamic>> startRoute(String routeId) =>
      _patch('/routes/$routeId/start');
  Future<Map<String, dynamic>> endRoute(String routeId) =>
      _patch('/routes/$routeId/end');

  // T5 - GPS Tracking
  Future<void> postGpsLog({
    required String routeId,
    required double latitude,
    required double longitude,
    double heading = 0.0,
    double speed = 0.0,
    double accuracy = 0.0,
  }) async {
    try {
      await http
          .post(
            Uri.parse('${ApiConfig.baseUrl}${ApiConfig.gpsPost}'),
            headers: _headers,
            body: json.encode({
              'route_id': routeId,
              'latitude': latitude,
              'longitude': longitude,
              'heading': heading,
              'speed': speed,
              'accuracy': accuracy,
            }),
          )
          .timeout(const Duration(seconds: 5));
    } catch (_) {}
  }

  Future<Map<String, dynamic>?> fetchLatestGps(String routeId) async {
    try {
      final response = await http
          .get(
            Uri.parse(
                '${ApiConfig.baseUrl}${ApiConfig.gpsLatest}$routeId/latest'),
            headers: _headers,
          )
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>> _post(
      String path, Map<String, dynamic> body) async {
    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}$path'),
      headers: _headers,
      body: json.encode(body),
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(_message(response));
    }
    return json.decode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> _patch(String path) async {
    final response = await http.patch(
        Uri.parse('${ApiConfig.baseUrl}$path'),
        headers: _headers);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(_message(response));
    }
    return json.decode(response.body) as Map<String, dynamic>;
  }

  String _message(http.Response response) {
    try {
      return (json.decode(response.body) as Map<String, dynamic>)['detail']
              ?.toString() ??
          'Yeu cau that bai (${response.statusCode})';
    } catch (_) {
      return 'Yeu cau that bai (${response.statusCode})';
    }
  }
}
