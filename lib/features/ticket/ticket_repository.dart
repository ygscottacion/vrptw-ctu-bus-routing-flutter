import '../../services/api_service.dart';

/// Repository cho nghiệp vụ vé — bọc quanh ApiService, không gọi Supabase trực tiếp.
/// Theo yêu cầu kiến trúc: "FastAPI là API nghiệp vụ duy nhất của Flutter trong MVP".
class TicketRepository {
  TicketRepository(this._api);
  final ApiService _api;

  Future<List<dynamic>> fetchMyTickets() => _api.fetchMyTickets();

  Future<Map<String, dynamic>> bookTicket({
    required int pickupLocationId,
    required DateTime serviceDate,
    required String sessionId,
    required String tripType,
  }) =>
      _api.bookTicket(
        pickupLocationId: pickupLocationId,
        serviceDate: serviceDate,
        sessionId: sessionId,
        tripType: tripType,
      );

  // TODO Ngày 4+: verifyTicket đã có trong ApiService, wrap khi cần dùng ở luồng tài xế.
}
