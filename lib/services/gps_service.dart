import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'api_service.dart';

/// Dịch vụ quản lý vị trí GPS thực tế của xe buýt tài xế (T5 - Lợi)
class GpsService {
  static final GpsService _instance = GpsService._internal();
  factory GpsService() => _instance;
  GpsService._internal();

  Timer? _timer;
  bool _isTracking = false;
  bool get isTracking => _isTracking;

  Position? _lastPosition;
  Position? get lastPosition => _lastPosition;

  final StreamController<Position> _positionController =
      StreamController<Position>.broadcast();
  Stream<Position> get positionStream => _positionController.stream;

  /// Xin quyền định vị thiết bị
  Future<bool> checkAndRequestPermission() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      return false;
    }

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        return false;
      }
    }

    if (permission == LocationPermission.deniedForever) {
      return false;
    }

    return true;
  }

  /// Bắt đầu gửi tọa độ GPS định kỳ (mặc định 15s/lần) lên Backend
  Future<bool> startTracking({
    required String routeId,
    required ApiService api,
    int intervalSeconds = 15,
  }) async {
    final hasPermission = await checkAndRequestPermission();
    if (!hasPermission) return false;

    _isTracking = true;
    _timer?.cancel();

    // Gửi vị trí ban đầu ngay lập tức
    await _fetchAndSendGps(routeId, api);

    // Đặt Timer định kỳ 15–20 giây
    _timer = Timer.periodic(Duration(seconds: intervalSeconds), (_) async {
      if (_isTracking) {
        await _fetchAndSendGps(routeId, api);
      }
    });

    return true;
  }

  /// Dừng gửi vị trí GPS
  void stopTracking() {
    _isTracking = false;
    _timer?.cancel();
    _timer = null;
  }

  Future<void> _fetchAndSendGps(String routeId, ApiService api) async {
    try {
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 8),
        ),
      );

      _lastPosition = position;
      _positionController.add(position);

      if (routeId.isNotEmpty) {
        await api.postGpsLog(
          routeId: routeId,
          latitude: position.latitude,
          longitude: position.longitude,
          heading: position.heading,
          speed: position.speed,
          accuracy: position.accuracy,
        );
      }
    } catch (e) {
      debugPrint('[GpsService] Lỗi phát/gửi vị trí: $e');
    }
  }

  void dispose() {
    stopTracking();
    _positionController.close();
  }
}
