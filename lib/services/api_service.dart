import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../features/auth/auth_repository.dart';

class ApiService {
  ApiService(this._authRepo);

  final AuthRepository _authRepo;

  /// Lấy token Supabase mới nhất mỗi lần gọi API — tránh dùng token cũ đã hết hạn.
  String? get _authToken => _authRepo.currentAccessToken;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_authToken != null) 'Authorization': 'Bearer $_authToken',
      };

  /// Lấy hồ sơ và role thật từ backend, dùng để điều hướng sau đăng nhập.
  /// TODO: xác nhận lại path chính xác với Nhã (ApiConfig.authMe).
  Future<Map<String, dynamic>?> fetchMe() async {
    if (_authToken == null) return null;
    try {
      final response = await http
          .get(
            Uri.parse('${ApiConfig.baseUrl}${ApiConfig.authMe}'),
            headers: _headers,
          )
          .timeout(const Duration(seconds: 6));
      if (response.statusCode != 200) return null;
      return json.decode(response.body) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  /// Lấy danh sách trạm dừng
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

  /// Lấy danh sách xe buýt
  Future<List<dynamic>> fetchVehicles() async {
    final url = Uri.parse('${ApiConfig.baseUrl}${ApiConfig.vehicles}');
    final response = await http.get(url, headers: _headers);
    if (response.statusCode == 200) {
      return json.decode(response.body) as List<dynamic>;
    }
    throw Exception('Không thể tải danh sách xe buýt: ${response.statusCode}');
  }

  /// Lấy lịch trình tuyến xe của Tài Xế
  Future<List<dynamic>> fetchDriverRoutes(int driverId) async {
    final url =
        Uri.parse('${ApiConfig.baseUrl}${ApiConfig.routesDriver}$driverId');
    final response = await http.get(url, headers: _headers);
    if (response.statusCode == 200) {
      return json.decode(response.body) as List<dynamic>;
    }
    throw Exception('Không thể tải lịch trình tài xế: ${response.statusCode}');
  }

  /// Lấy danh sách tuyến khả dụng cho hành khách
  Future<List<dynamic>> fetchActiveRoutes() async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.routesActive}'),
      headers: _headers,
    );
    if (response.statusCode == 200) {
      return json.decode(response.body) as List<dynamic>;
    }
    throw Exception('Không thể tải danh sách tuyến: ${response.statusCode}');
  }

  Future<List<dynamic>> fetchMyTickets() async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.ticketsMe}'),
      headers: _headers,
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    return json.decode(response.body) as List<dynamic>;
  }

  /// One ticket is one reserved direction for a chosen service day and stop.
  Future<Map<String, dynamic>> bookTicket({
    required int pickupLocationId,
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
    final data = json.decode(response.body) as List<dynamic>;
    return Map<String, dynamic>.from(data.first as Map);
  }

  Future<Map<String, dynamic>> fetchRouteDetails(int routeId) async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.routeDetails}$routeId'),
      headers: _headers,
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(json.decode(response.body) as Map);
  }

  Future<Map<String, dynamic>> verifyTicket(String qrCode) =>
      _post(ApiConfig.ticketsVerifyQr, {'qr_code': qrCode});

  Future<Map<String, dynamic>> reportIncident({
    required String title,
    String? description,
    int? vehicleId,
  }) =>
      _post(ApiConfig.incidents, {
        'title': title,
        if (description != null) 'description': description,
        if (vehicleId != null) 'vehicle_id': vehicleId,
      });

  Future<Map<String, dynamic>> startRoute(int routeId) =>
      _patch('/routes/$routeId/start');
  Future<Map<String, dynamic>> endRoute(int routeId) =>
      _patch('/routes/$routeId/end');

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
    final response = await http.patch(Uri.parse('${ApiConfig.baseUrl}$path'),
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
          'Yêu cầu thất bại (${response.statusCode})';
    } catch (_) {
      return 'Yêu cầu thất bại (${response.statusCode})';
    }
  }
}
