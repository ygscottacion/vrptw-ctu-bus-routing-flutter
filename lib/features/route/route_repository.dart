import '../../services/api_service.dart';

/// Repository cho tuyến/trạm — dùng ở màn Đặt vé và Bản đồ.
class RouteRepository {
  RouteRepository(this._api);
  final ApiService _api;

  Future<List<dynamic>> fetchLocations() => _api.fetchLocations();
  Future<List<dynamic>> fetchActiveRoutes() => _api.fetchActiveRoutes();

  /// routeId la UUID (String) tu Ngay 4 - khong con la int.
  Future<Map<String, dynamic>> fetchRouteDetails(String routeId) =>
      _api.fetchRouteDetails(routeId);

  Future<Map<String, dynamic>?> fetchVehiclePosition(String routeId) =>
      _api.fetchLatestGps(routeId);
}
