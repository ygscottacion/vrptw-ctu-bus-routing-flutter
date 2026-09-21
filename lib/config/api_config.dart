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
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000/api/v1';
    }
    return 'http://localhost:8000/api/v1';
  }

  /// Cấu hình Supabase Staging
  static const String supabaseUrl = String.fromEnvironment(
    'SUPABASE_URL',
    defaultValue: 'https://szybskwlctbynbkqnllv.supabase.co',
  );

  static const String supabaseAnonKey = String.fromEnvironment(
    'SUPABASE_ANON_KEY',
    defaultValue:
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN6eWJza3dsY3RieW5ia3FubGx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc4MDU5NDEsImV4cCI6MjEwMzM4MTk0MX0.3HjI2OoPAZ5pfapxtdfgajJxD7F_9OsbjWnOja9v8pI',
  );

  /// Cấu hình Goong Maps API
  static const String goongMapTilesKey = String.fromEnvironment(
    'GOONG_MAPTILES_KEY',
    defaultValue: 'rwZKp27qLAlPcckb3HOe3E4JwiOaR54wPiW9hwJx',
  );

  static const String goongApiKey = String.fromEnvironment(
    'GOONG_API_KEY',
    defaultValue: '7WSy0ek8OLEv1HZvB9oikhHT6hVrohUdCLShbK8S',
  );

  /// URL template cho TileLayer raster tiles theo Goong Maps (Chuẩn dự án)
  static String get goongTileUrl =>
      'https://tiles.goong.io/assets/tiles/{z}/{x}/{y}.png?api_key=$goongMapTilesKey';

  /// URL template fallback (OpenStreetMap) khi Goong API key gặp sự cố hoặc 403
  static String get fallbackTileUrl =>
      'https://tile.openstreetmap.org/{z}/{x}/{y}.png';

  /// URL template mặc định
  static String get mapTileUrl => goongTileUrl;

  /// Style JSON URL cho Goong Map Vector/Web Style
  static String get goongMapStyleUrl =>
      'https://tiles.goong.io/assets/goong_map_web.json?api_key=$goongMapTilesKey';


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
  static const String routeDetails =
      '/routes/'; // Sua: bo '/details/' theo dung endpoint GET /routes/{route_id}
  static const String incidents = '/incidents/';

  // T5 — GPS Tracking (D5 - Lợi)
  // POST /gps/            → tài xế gửi vị trí định kỳ
  // GET  /gps/{id}/latest → sinh viên xem xe đang ở đâu
  static const String gpsPost = '/gps/';
  static const String gpsLatest = '/gps/';
}
