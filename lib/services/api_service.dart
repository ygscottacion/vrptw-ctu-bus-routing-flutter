import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';

class ApiService {
  String? _authToken;

  String? get authToken => _authToken;

  /// 1. Đăng nhập hệ thống (Auth Login)
  Future<Map<String, dynamic>> login(String username, String password) async {
    final url = Uri.parse('${ApiConfig.baseUrl}${ApiConfig.authLogin}');
    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: {
          'username': username,
          'password': password,
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _authToken = data['access_token'];
        final user = await fetchMe();
        if (user == null) {
          return {'success': false, 'message': 'Không thể tải thông tin tài khoản'};
        }
        return {'success': true, 'token': _authToken, 'user': user};
      } else {
        final error = json.decode(response.body);
        return {'success': false, 'message': error['detail'] ?? 'Đăng nhập thất bại'};
      }
    } catch (e) {
      return {'success': false, 'message': 'Lỗi kết nối Server: $e'};
    }
  }

  /// Lấy hồ sơ và role thật từ backend, dùng để điều hướng sau đăng nhập.
  Future<Map<String, dynamic>?> fetchMe() async {
    if (_authToken == null) return null;
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.authMe}'),
      headers: {'Authorization': 'Bearer $_authToken'},
    );
    if (response.statusCode != 200) return null;
    return json.decode(response.body) as Map<String, dynamic>;
  }

  /// 2. Lấy danh sách 10 trạm dừng ở TP. Cần Thơ
  Future<List<dynamic>> fetchLocations() async {
    final url = Uri.parse('${ApiConfig.baseUrl}${ApiConfig.locations}');
    final headers = <String, String>{
      'Content-Type': 'application/json',
    };
    if (_authToken != null) {
      headers['Authorization'] = 'Bearer $_authToken';
    }

    try {
      final response = await http.get(url, headers: headers).timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        return json.decode(response.body) as List<dynamic>;
      } else {
        return [];
      }
    } catch (e) {
      return [];
    }
  }

  /// 3. Lấy danh sách xe buýt
  Future<List<dynamic>> fetchVehicles() async {
    final url = Uri.parse('${ApiConfig.baseUrl}${ApiConfig.vehicles}');
    final headers = <String, String>{
      'Content-Type': 'application/json',
    };
    if (_authToken != null) {
      headers['Authorization'] = 'Bearer $_authToken';
    }

    try {
      final response = await http.get(url, headers: headers);
      if (response.statusCode == 200) {
        return json.decode(response.body) as List<dynamic>;
      } else {
        throw Exception('Không thể tải danh sách xe buýt: ${response.statusCode}');
      }
    } catch (e) {
      rethrow;
    }
  }

  /// 4. Lấy lịch trình tuyến xe của Tài Xế
  Future<List<dynamic>> fetchDriverRoutes(int driverId) async {
    final url = Uri.parse('${ApiConfig.baseUrl}${ApiConfig.routesDriver}$driverId');
    final headers = <String, String>{
      'Content-Type': 'application/json',
    };
    if (_authToken != null) {
      headers['Authorization'] = 'Bearer $_authToken';
    }

    try {
      final response = await http.get(url, headers: headers);
      if (response.statusCode == 200) {
        return json.decode(response.body) as List<dynamic>;
      } else {
        throw Exception('Không thể tải lịch trình tài xế: ${response.statusCode}');
      }
    } catch (e) {
      rethrow;
    }
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_authToken != null) 'Authorization': 'Bearer $_authToken',
      };

  Future<List<dynamic>> fetchMyTickets() async {
    final response = await http.get(Uri.parse('${ApiConfig.baseUrl}${ApiConfig.ticketsMe}'), headers: _headers);
    if (response.statusCode != 200) throw Exception(_message(response));
    return json.decode(response.body) as List<dynamic>;
  }

  Future<Map<String, dynamic>> bookTicket(int routeId) => _post(ApiConfig.ticketsBook, {'route_id': routeId});

  Future<Map<String, dynamic>> verifyTicket(String qrCode) => _post(ApiConfig.ticketsVerifyQr, {'qr_code': qrCode});

  Future<Map<String, dynamic>> reportIncident({required String title, String? description, int? vehicleId}) =>
      _post(ApiConfig.incidents, {'title': title, if (description != null) 'description': description, if (vehicleId != null) 'vehicle_id': vehicleId});

  Future<Map<String, dynamic>> startRoute(int routeId) => _patch('/routes/$routeId/start');
  Future<Map<String, dynamic>> endRoute(int routeId) => _patch('/routes/$routeId/end');

  Future<Map<String, dynamic>> _post(String path, Map<String, dynamic> body) async {
    final response = await http.post(Uri.parse('${ApiConfig.baseUrl}$path'), headers: _headers, body: json.encode(body));
    if (response.statusCode < 200 || response.statusCode >= 300) throw Exception(_message(response));
    return json.decode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> _patch(String path) async {
    final response = await http.patch(Uri.parse('${ApiConfig.baseUrl}$path'), headers: _headers);
    if (response.statusCode < 200 || response.statusCode >= 300) throw Exception(_message(response));
    return json.decode(response.body) as Map<String, dynamic>;
  }

  String _message(http.Response response) {
    try {
      return (json.decode(response.body) as Map<String, dynamic>)['detail']?.toString() ??
          'Yêu cầu thất bại (${response.statusCode})';
    } catch (_) {
      return 'Yêu cầu thất bại (${response.statusCode})';
    }
  }
}
