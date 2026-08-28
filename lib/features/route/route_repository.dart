import '../../services/api_service.dart';

/// Repository cho tuyến/trạm — dùng ở màn Đặt vé và Bản đồ.
class RouteRepository {
  RouteRepository(this._api);
  final ApiService _api;

  Future<List<dynamic>> fetchLocations() => _api.fetchLocations();
  Future<List<dynamic>> fetchActiveRoutes() => _api.fetchActiveRoutes();
  Future<Map<String, dynamic>> fetchRouteDetails(int routeId) =>
      _api.fetchRouteDetails(routeId);

  // TODO: khi map_screen.dart bỏ Timer.periodic giả, thêm hàm polling vị trí xe ở đây:
  // Future<Map<String, dynamic>> fetchVehiclePosition(int routeId);
}
