import 'package:flutter/material.dart';
import '../features/driver/driver_alerts_tab.dart';
import '../features/driver/driver_home_tab.dart';
import '../features/driver/driver_map_tab.dart';
import '../features/driver/driver_profile_tab.dart';
import '../features/driver/driver_qr_tab.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class DriverShell extends StatefulWidget {
  const DriverShell({
    super.key,
    required this.user,
    required this.api,
    required this.onLogout,
  });

  final Map<String, dynamic> user;
  final ApiService api;
  final VoidCallback onLogout;

  @override
  State<DriverShell> createState() => _DriverShellState();
}

class _DriverShellState extends State<DriverShell> {
  int _currentIndex = 0;
  Map<String, dynamic>? _selectedRoute;

  void _onSelectRouteFromHome(Map<String, dynamic> route) {
    setState(() {
      _selectedRoute = route;
      _currentIndex = 1; // Switch to Map tab
    });
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      DriverHomeTab(
        user: widget.user,
        api: widget.api,
        onSelectRoute: _onSelectRouteFromHome,
      ),
      DriverMapTab(
        api: widget.api,
        initialRoute: _selectedRoute,
      ),
      DriverQrTab(
        api: widget.api,
      ),
      DriverAlertsTab(
        api: widget.api,
      ),
      DriverProfileTab(
        user: widget.user,
        onLogout: widget.onLogout,
      ),
    ];

    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: pages,
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.06),
              blurRadius: 12,
              offset: const Offset(0, -4),
            ),
          ],
        ),
        child: NavigationBar(
          selectedIndex: _currentIndex,
          onDestinationSelected: (idx) => setState(() => _currentIndex = idx),
          backgroundColor: Colors.white,
          indicatorColor: AppColors.teal.withOpacity(0.15),
          elevation: 8,
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home_rounded, color: AppColors.teal),
              label: 'Trang chủ',
            ),
            NavigationDestination(
              icon: Icon(Icons.map_outlined),
              selectedIcon: Icon(Icons.map_rounded, color: AppColors.teal),
              label: 'Route',
            ),
            NavigationDestination(
              icon: Icon(Icons.qr_code_scanner_outlined),
              selectedIcon: Icon(Icons.qr_code_scanner_rounded, color: AppColors.teal),
              label: 'Scan',
            ),
            NavigationDestination(
              icon: Icon(Icons.notifications_outlined),
              selectedIcon: Icon(Icons.notifications_rounded, color: AppColors.teal),
              label: 'Alerts',
            ),
            NavigationDestination(
              icon: Icon(Icons.person_outline_rounded),
              selectedIcon: Icon(Icons.person_rounded, color: AppColors.teal),
              label: 'Profile',
            ),
          ],
        ),
      ),
    );
  }
}
