import 'dart:io';
import 'package:flutter/foundation.dart';

class ApiConfig {
  /// Tự động cấu hình Base URL phù hợp với từng thiết bị kiểm thử:
  /// - Android Emulator: http://10.0.2.2:8000/api/v1
  /// - iOS Simulator / Web Chrome: http://localhost:8000/api/v1
  /// - Điện thoại thật (Wi-Fi): Thay '10.0.2.2' thành IP máy tính (ví dụ: '192.168.1.15')
  static String get baseUrl {
    if (kIsWeb) {
      return 'http://localhost:8000/api/v1';
    } else if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000/api/v1';
    } else {
      return 'http://localhost:8000/api/v1';
    }
  }

  // Endpoints
  static const String authLogin = '/auth/login';
  static const String authMe = '/auth/me';
  static const String locations = '/locations/';
  static const String vehicles = '/vehicles/';
  static const String routesGenerate = '/routes/generate';
  static const String routesActive = '/routes/';
  static const String routesDriver = '/routes/driver/';
  static const String ticketsMe = '/tickets/me';
  static const String ticketsBuy = '/tickets/reserve';
  static const String ticketsVerifyQr = '/tickets/verify-qr';
  static const String routeDetails = '/routes/';
  static const String incidents = '/incidents/';
}
