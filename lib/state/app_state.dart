import 'package:flutter/foundation.dart';
import '../features/auth/auth_repository.dart';

/// Dùng với package:provider — bọc ChangeNotifierProvider ở gốc widget tree.
class AppState extends ChangeNotifier {
  AppState(this.authRepo);

  final AuthRepository authRepo;

  Map<String, dynamic>? _user;
  Map<String, dynamic>? get user => _user;

  bool _isCheckingSession = true;
  bool get isCheckingSession => _isCheckingSession;

  bool get isLoggedIn => _user != null;
  String get role => _user?['role']?.toString() ?? 'student';

  /// Gọi 1 lần khi app khởi động để khôi phục phiên cũ (nếu có).
  Future<void> restoreSession() async {
    final session = authRepo.currentSession;
    if (session != null) {
      // TODO Ngày 3: gọi /me qua ApiService để lấy role/profile thật.
      // Đang bị block bởi bảng `profiles` (Minh - Ngày 2) chưa xong.
      _user = {'email': authRepo.currentUser?.email, 'role': 'student'};
    }
    _isCheckingSession = false;
    notifyListeners();
  }

  void setUser(Map<String, dynamic> user) {
    _user = user;
    notifyListeners();
  }

  Future<void> logout() async {
    await authRepo.signOut();
    _user = null;
    notifyListeners();
  }
}
