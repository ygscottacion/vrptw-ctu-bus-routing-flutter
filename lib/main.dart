import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:overlay_support/overlay_support.dart';
import 'screens/driver_shell.dart';
import 'screens/home_screen.dart';
import 'screens/map_screen.dart';
import 'screens/ticket_screen.dart';
import 'screens/notification_screen.dart';
import 'screens/settings_screen.dart';
import 'services/api_service.dart';
import 'theme/app_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(statusBarColor: AppColors.teal, statusBarIconBrightness: Brightness.light),
  );
  runApp(const MyCtuBusApp());
}

class MyCtuBusApp extends StatefulWidget {
  const MyCtuBusApp({super.key});

  @override
  State<MyCtuBusApp> createState() => _MyCtuBusAppState();
}

class _MyCtuBusAppState extends State<MyCtuBusApp> {
  final _api = ApiService();
  Map<String, dynamic>? _user;

  @override
  Widget build(BuildContext context) => OverlaySupport.global(
        child: MaterialApp(
          title: 'MyCTU BUS',
          debugShowCheckedModeBanner: false,
          theme: buildAppTheme(),
          home: _home(),
        ),
      );

  Widget _home() {
    if (_user?['role'] == 'driver') return DriverShell(user: _user!, api: _api, onLogout: _logout);
    if (_user?['role'] == 'admin') return AdminWebNotice(onLogout: _logout);
    return StudentShell(api: _api, onLoggedIn: (user) => setState(() => _user = user));
  }

  void _logout() => setState(() => _user = null);
}

class StudentShell extends StatefulWidget {
  const StudentShell({super.key, required this.api, required this.onLoggedIn});
  final ApiService api;
  final ValueChanged<Map<String, dynamic>> onLoggedIn;

  @override
  State<StudentShell> createState() => _StudentShellState();
}

class _StudentShellState extends State<StudentShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final screens = [
      const HomeScreen(),
      const MapScreen(),
      TicketScreen(api: widget.api),
      const NotificationScreen(),
      SettingsScreen(apiService: widget.api, onLoggedIn: widget.onLoggedIn),
    ];

    return Scaffold(
      body: IndexedStack(index: _index, children: screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_rounded), label: 'Trang chủ'),
          NavigationDestination(icon: Icon(Icons.map_rounded), label: 'Bản đồ'),
          NavigationDestination(icon: Icon(Icons.confirmation_num_rounded), label: 'Vé của tôi'),
          NavigationDestination(icon: Icon(Icons.notifications_rounded), label: 'Thông báo'),
          NavigationDestination(icon: Icon(Icons.settings_rounded), label: 'Cài đặt'),
        ],
      ),
    );
  }
}

class AdminWebNotice extends StatelessWidget {
  const AdminWebNotice({super.key, required this.onLogout});
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.admin_panel_settings_rounded, size: 70, color: AppColors.teal),
                const SizedBox(height: 20),
                const Text('Tài khoản quản trị', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                const SizedBox(height: 10),
                const Text('Vui lòng sử dụng MyCTU BUS Admin Web để quản lý xe, tuyến và người dùng.', textAlign: TextAlign.center),
                const SizedBox(height: 24),
                OutlinedButton.icon(
                  onPressed: onLogout,
                  icon: const Icon(Icons.logout),
                  label: const Text('Đăng xuất'),
                ),
              ],
            ),
          ),
        ),
      );
}
