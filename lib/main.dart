import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:overlay_support/overlay_support.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'config/api_config.dart';
import 'features/auth/auth_repository.dart';
import 'screens/driver_shell.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'screens/ticket_screen.dart';
import 'screens/notification_screen.dart';
import 'screens/settings_screen.dart';
import 'services/api_service.dart';
import 'state/app_state.dart';
import 'theme/app_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  ApiConfig.assertConfigured();

  await Supabase.initialize(
    url: ApiConfig.supabaseUrl,
    anonKey: ApiConfig.supabaseAnonKey,
  );

  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
        statusBarColor: AppColors.teal,
        statusBarIconBrightness: Brightness.light),
  );

  final authRepo = AuthRepository();
  final appState = AppState(authRepo);
  await appState.restoreSession();

  runApp(
    ChangeNotifierProvider.value(
      value: appState,
      child: const MyCtuBusApp(),
    ),
  );
}

class MyCtuBusApp extends StatelessWidget {
  const MyCtuBusApp({super.key});

  @override
  Widget build(BuildContext context) => OverlaySupport.global(
        child: MaterialApp(
          title: 'MyCTU BUS',
          debugShowCheckedModeBanner: false,
          theme: buildAppTheme(),
          home: const _RootScreen(),
        ),
      );
}

class _RootScreen extends StatelessWidget {
  const _RootScreen();

  @override
  Widget build(BuildContext context) {
    final appState = context.watch<AppState>();

    if (appState.isCheckingSession) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (!appState.isLoggedIn) {
      return const LoginScreen(); // <- bo tham so authRepo/onLoggedIn
    }

    final api = appState
        .api; // <- dung lai instance co san trong AppState, khong tao moi

    if (appState.role == 'driver') {
      return DriverShell(
          user: appState.user!, api: api, onLogout: appState.logout);
    }
    if (appState.role == 'admin') {
      return AdminWebNotice(onLogout: appState.logout);
    }
    return StudentShell(api: api);
  }
}

class StudentShell extends StatefulWidget {
  const StudentShell({super.key, required this.api});
  final ApiService api;

  @override
  State<StudentShell> createState() => _StudentShellState();
}

class _StudentShellState extends State<StudentShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final screens = [
      const HomeScreen(),
      TicketScreen(api: widget.api),
      const NotificationScreen(),
      const SettingsScreen(),
    ];

    return Scaffold(
      body: IndexedStack(index: _index, children: screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
              icon: Icon(Icons.home_rounded), label: 'Trang chủ'),
          NavigationDestination(
              icon: Icon(Icons.confirmation_num_rounded), label: 'Vé của tôi'),
          NavigationDestination(
              icon: Icon(Icons.notifications_rounded), label: 'Thông báo'),
          NavigationDestination(
              icon: Icon(Icons.settings_rounded), label: 'Cài đặt'),
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
                const Icon(Icons.admin_panel_settings_rounded,
                    size: 70, color: AppColors.teal),
                const SizedBox(height: 20),
                const Text('Tài khoản quản trị',
                    style:
                        TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                const SizedBox(height: 10),
                const Text(
                    'Vui lòng sử dụng MyCTU BUS Admin Web để quản lý xe, tuyến và người dùng.',
                    textAlign: TextAlign.center),
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
