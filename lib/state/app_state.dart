import 'package:flutter/foundation.dart';
import '../features/auth/auth_repository.dart';
import '../services/api_service.dart';

class AppState extends ChangeNotifier {
  AppState(this.authRepo) : api = ApiService(authRepo);

  final AuthRepository authRepo;
  final ApiService api;

  Map<String, dynamic>? _user;
  Map<String, dynamic>? get user => _user;

  bool _isCheckingSession = true;
  bool get isCheckingSession => _isCheckingSession;

  bool get isLoggedIn => _user != null;

  /// Gia tri that tu backend: 'admin' | 'driver' | 'passenger'
  String get role => _user?['role']?.toString() ?? 'passenger';

  /// Goi khi app khoi dong de khoi phuc phien cu (neu co).
  Future<void> restoreSession() async {
    final session = authRepo.currentSession;
    if (session != null) {
      await _loadProfile();
    }
    _isCheckingSession = false;
    notifyListeners();
  }

  /// Goi ngay sau khi dang nhap thanh cong, de lay role that tu /me.
  Future<void> onLoggedIn() async {
    await _loadProfile();
    notifyListeners();
  }

  Future<void> _loadProfile() async {
    try {
      final profile = await api.fetchMe();
      if (profile != null) {
        _user = profile;
        return;
      }
    } catch (_) {
      // Backend chua san sang hoac loi mang - fallback ben duoi.
    }
    // Fallback: van cho vao app voi role mac dinh passenger, tranh ket cung o loading.
    _user = {'email': authRepo.currentUser?.email, 'role': 'passenger'};
  }

  Future<void> logout() async {
    await authRepo.signOut();
    _user = null;
    notifyListeners();
  }
}
