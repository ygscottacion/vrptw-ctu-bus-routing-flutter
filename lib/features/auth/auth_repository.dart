import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AuthFailure implements Exception {
  final String message;
  AuthFailure(this.message);
  @override
  String toString() => message;
}

class AuthRepository {
  final SupabaseClient _supabase = Supabase.instance.client;

  Session? get currentSession => _supabase.auth.currentSession;
  User? get currentUser => _supabase.auth.currentUser;
  Stream<AuthState> get authStateChanges => _supabase.auth.onAuthStateChange;
  String? get currentAccessToken => currentSession?.accessToken;

  Future<AuthResponse> signInWithEmailPassword(
      String email, String password) async {
    try {
      return await _supabase.auth
          .signInWithPassword(email: email, password: password);
    } on AuthException catch (e) {
      throw AuthFailure(_mapAuthError(e.message));
    } catch (_) {
      throw AuthFailure(
          'Không thể kết nối. Vui lòng kiểm tra mạng và thử lại.');
    }
  }

  Future<void> signOut() async {
    await _supabase.auth.signOut();
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }

  String _mapAuthError(String message) {
    if (message.contains('Invalid login credentials'))
      return 'Email hoặc mật khẩu không đúng.';
    if (message.contains('Email not confirmed'))
      return 'Email chưa được xác thực.';
    return 'Đăng nhập thất bại: $message';
  }
}
