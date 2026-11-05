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
  StreamSubscription<Position>? _positionSubscription;
  bool _isTracking = false;
  bool _isSending = false;
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

  /// Bắt đầu gửi tọa độ GPS định kỳ (mặc định 10s/lần, tối đa 15s) lên Backend
  Future<bool> startTracking({
    required String routeId,
    required ApiService api,
    int intervalSeconds = 10,
  }) async {
    if (routeId.trim().isEmpty) return false;
    final hasPermission = await checkAndRequestPermission();
    if (!hasPermission) return false;

    _isTracking = true;
    _timer?.cancel();
    await _positionSubscription?.cancel();
    _lastPosition = null;
    _positionSubscription = Geolocator.getPositionStream(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 0,
      ),
    ).listen((position) {
      if (!_isTracking) return;
      _lastPosition = position;
      _positionController.add(position);
    });
    final safeIntervalSeconds = intervalSeconds < 10
        ? 10
        : intervalSeconds > 15
            ? 15
            : intervalSeconds;

    // Gửi vị trí ban đầu ngay lập tức
    final sentInitialLocation = await _fetchAndSendGps(routeId, api);

    // Đặt Timer định kỳ, giới hạn trong khoảng 10–15 giây.
    _timer = Timer.periodic(Duration(seconds: safeIntervalSeconds), (_) async {
      if (_isTracking) {
        await _fetchAndSendGps(routeId, api);
      }
    });

    return sentInitialLocation;
  }

  /// Dừng gửi vị trí GPS
  void stopTracking() {
    _isTracking = false;
    _timer?.cancel();
    _timer = null;
    _positionSubscription?.cancel();
    _positionSubscription = null;
  }

  Future<bool> _fetchAndSendGps(String routeId, ApiService api) async {
    if (_isSending || !_isTracking) return false;
    _isSending = true;
    try {
      var position = _lastPosition;
      final lastPositionAge = position == null
          ? null
          : DateTime.now().difference(position.timestamp);
      if (position == null ||
          lastPositionAge! > const Duration(seconds: 15) ||
          lastPositionAge < -const Duration(seconds: 30)) {
        position = await Geolocator.getCurrentPosition(
          locationSettings: const LocationSettings(
            accuracy: LocationAccuracy.high,
            timeLimit: Duration(seconds: 8),
          ),
        );
      }
      if (!_isTracking) return false;

      _lastPosition = position;
      if (lastPositionAge == null ||
          lastPositionAge > const Duration(seconds: 15)) {
        _positionController.add(position);
      }

      if (routeId.isNotEmpty) {
        await api.postGpsLog(
          routeId: routeId,
          latitude: position.latitude,
          longitude: position.longitude,
          heading: position.heading.isFinite &&
                  position.heading >= 0 &&
                  position.heading < 360
              ? position.heading
              : 0,
          speed: position.speed.isFinite && position.speed > 0
              ? position.speed * 3.6
              : 0,
          accuracy: position.accuracy,
        );
      }
      return true;
    } catch (e) {
      debugPrint('[GpsService] Lỗi phát/gửi vị trí: $e');
      return false;
    } finally {
      _isSending = false;
    }
  }

  void dispose() {
    stopTracking();
    _positionController.close();
  }
}
