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
        return {'success': true, 'token': _authToken};
      } else {
        final error = json.decode(response.body);
        return {'success': false, 'message': error['detail'] ?? 'Đăng nhập thất bại'};
      }
    } catch (e) {
      return {'success': false, 'message': 'Lỗi kết nối Server: $e'};
    }
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
}
