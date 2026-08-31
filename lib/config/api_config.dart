import 'dart:io';
import 'package:flutter/foundation.dart';

class ApiConfig {
  /// Base URL của FastAPI Backend.
  /// Ưu tiên giá trị truyền qua --dart-define (dùng cho staging/production).
  /// Nếu không truyền, tự động fallback theo platform (dùng khi chạy local):
  /// - Android Emulator: http://10.0.2.2:8000/api/v1
  /// - iOS Simulator / Web Chrome: http://localhost:8000/api/v1
  /// - Điện thoại thật (Wi-Fi): cần truyền --dart-define=BASE_URL=http://<ip-may-tinh>:8000/api/v1
  static String get baseUrl {
    const fromEnv = String.fromEnvironment('BASE_URL', defaultValue: '');
    if (fromEnv.isNotEmpty) return fromEnv;

    if (kIsWeb) return 'http://localhost:8000/api/v1';
    if (Platform.isAndroid) return 'http://10.0.2.2:8000/api/v1';
    return 'http://localhost:8000/api/v1';
  }

  /// Cấu hình Supabase — bắt buộc truyền qua --dart-define, không có giá trị mặc định
  /// để tránh app chạy "âm thầm sai" khi quên cấu hình.
  static const String supabaseUrl = String.fromEnvironment(
    'SUPABASE_URL',
    defaultValue: '',
  );

  static const String supabaseAnonKey = String.fromEnvironment(
    'SUPABASE_ANON_KEY',
    defaultValue: '',
  );

  /// Gọi ở đầu main() để báo lỗi rõ ràng nếu quên truyền dart-define,
  /// thay vì để app crash mơ hồ khi Supabase.initialize() nhận chuỗi rỗng.
  static void assertConfigured() {
    assert(
      supabaseUrl.isNotEmpty && supabaseAnonKey.isNotEmpty,
      'Thieu SUPABASE_URL hoac SUPABASE_ANON_KEY. '
      'Chay app kem --dart-define, xem README hoac hoi Minh de lay gia tri staging.',
    );
  }

  // Endpoints
  // Da bo authLogin: Flutter chi dung Supabase Auth truc tiep, khong con JWT noi bo (yeu cau bat buoc #2).
  static const String authMe =
      '/auth/me'; // TODO: xac nhan lai path chinh xac voi Nha (co the la '/me')
  static const String locations = '/locations/';
  static const String vehicles = '/vehicles/';
  static const String routesGenerate = '/routes/generate';
  static const String routesActive = '/routes/';
  static const String routesDriver = '/routes/driver/';
  static const String ticketsMe = '/tickets/me';
  static const String ticketsBuy =
      '/tickets/reserve'; // Da doi tu '/tickets/buy' theo ban giao T4 cua Minh/Nha
  static const String ticketsVerifyQr = '/tickets/verify-qr';
  static const String routeDetails = '/routes/';
  static const String incidents = '/incidents/';
}
