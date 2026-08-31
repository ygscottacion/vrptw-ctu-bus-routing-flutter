import 'package:flutter/material.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';

class DriverQrTab extends StatefulWidget {
  const DriverQrTab({super.key, required this.api});

  final ApiService api;

  @override
  State<DriverQrTab> createState() => _DriverQrTabState();
}

class _DriverQrTabState extends State<DriverQrTab>
    with SingleTickerProviderStateMixin {
  final TextEditingController _codeController = TextEditingController();
  late AnimationController _scannerAnimController;
  late Animation<double> _scannerAnimation;
  bool _isChecking = false;

  // Lịch sử các vé đã soát trong phiên làm việc (Duplicate Scan Protection)
  final Set<String> _scannedTickets = {};
  Map<String, dynamic>? _lastVerificationResult;

  @override
  void initState() {
    super.initState();
    _scannerAnimController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    _scannerAnimation = Tween<double>(begin: 0.1, end: 0.9).animate(
      CurvedAnimation(
        parent: _scannerAnimController,
        curve: Curves.easeInOut,
      ),
    );
  }

  @override
  void dispose() {
    _scannerAnimController.dispose();
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _verifyQr(String code) async {
    final cleanCode = code.trim();
    if (cleanCode.isEmpty) return;

    // 1. Kiểm tra Quét trùng (Duplicate Scan Protection)
    if (_scannedTickets.contains(cleanCode)) {
      setState(() {
        _lastVerificationResult = {
          'status': 'duplicate',
          'code': cleanCode,
          'message': 'Mã vé này đã được tài xế soát thành công trước đó trong ca làm việc!',
          'timestamp': DateTime.now().toString().substring(11, 16),
        };
      });
      _showResultDialog('duplicate');
      return;
    }

    setState(() => _isChecking = true);
    try {
      final res = await widget.api.verifyTicket(cleanCode);
      if (mounted) {
        _scannedTickets.add(cleanCode); // Đánh dấu mã vé đã soát
        setState(() {
          _lastVerificationResult = {
            'status': 'success',
            'ticket_id': res['id'] ?? cleanCode,
            'student_name': res['student_name'] ?? 'Nguyễn Văn Sinh Viên',
            'student_code': res['student_code'] ?? 'B2012345',
            'route_name': res['route_name'] ?? 'Tuyến #1 - Khu II → Hòa An',
            'timestamp': DateTime.now().toString().substring(11, 16),
          };
        });
        _showResultDialog('success');
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _lastVerificationResult = {
            'status': 'invalid',
            'error': e.toString(),
            'code': cleanCode,
          };
        });
        _showResultDialog('invalid');
      }
    } finally {
      if (mounted) setState(() => _isChecking = false);
    }
  }

  void _showResultDialog(String status) {
    final isSuccess = status == 'success';
    final isDuplicate = status == 'duplicate';

    Color themeColor;
    IconData iconData;
    String title;

    if (isSuccess) {
      themeColor = AppColors.teal;
      iconData = Icons.check_circle_rounded;
      title = 'XÁC NHẬN VÉ HỢP LỆ';
    } else if (isDuplicate) {
      themeColor = const Color(0xFFF59F00); // Orange warning
      iconData = Icons.warning_amber_rounded;
      title = 'CẢNH BÁO: VÉ ĐÃ SỬ DỤNG';
    } else {
      themeColor = Colors.red;
      iconData = Icons.cancel_rounded;
      title = 'VÉ KHÔNG HỢP LỆ';
    }

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (c) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 70,
              height: 70,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: themeColor.withOpacity(0.15),
              ),
              child: Icon(
                iconData,
                color: themeColor,
                size: 48,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              title,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: themeColor,
              ),
            ),
            const SizedBox(height: 12),
            if (isSuccess && _lastVerificationResult != null) ...[
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFF0F4F4),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  children: [
                    _infoRow('Sinh viên:',
                        '${_lastVerificationResult!['student_name']} (${_lastVerificationResult!['student_code']})'),
                    const SizedBox(height: 6),
                    _infoRow('Tuyến xe:',
                        _lastVerificationResult!['route_name'].toString()),
                    const SizedBox(height: 6),
                    _infoRow('Thời gian:',
                        _lastVerificationResult!['timestamp'].toString()),
                  ],
                ),
              ),
            ] else if (isDuplicate) ...[
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFF9DB),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFFFEC99)),
                ),
                child: Column(
                  children: [
                    Text(
                      _lastVerificationResult?['message'] ?? '',
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: Color(0xFFE67700),
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 8),
                    _infoRow('Mã vé:', _lastVerificationResult?['code'] ?? ''),
                    const SizedBox(height: 4),
                    _infoRow('Thời gian quét lại:',
                        _lastVerificationResult?['timestamp'] ?? ''),
                  ],
                ),
              ),
            ] else ...[
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFF0F0),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  'Mã QR "${_lastVerificationResult?['code'] ?? ''}" không tồn tại, hết hạn hoặc không thuộc quyền sở hữu.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.red, fontSize: 13),
                ),
              ),
            ],
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: () {
                  Navigator.pop(c);
                  _codeController.clear();
                },
                style: FilledButton.styleFrom(
                  backgroundColor: themeColor,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: const Text('Quét vé tiếp theo', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _infoRow(String label, String val) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(color: Colors.grey, fontSize: 13)),
        Flexible(
          child: Text(
            val,
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
            textAlign: TextAlign.right,
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF181C1D),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text(
          'Quét mã QR vé Sinh viên (Scan)',
          style: TextStyle(color: Colors.white),
        ),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const Text(
              'Hướng camera về phía mã QR trên ứng dụng Sinh viên',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white70, fontSize: 14),
            ),
            const SizedBox(height: 24),

            // Camera Viewfinder Box Simulation
            Center(
              child: Container(
                width: 260,
                height: 260,
                decoration: BoxDecoration(
                  color: Colors.black45,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: AppColors.teal, width: 2),
                ),
                child: Stack(
                  children: [
                    // Corner bracket accents
                    Positioned(
                      top: 16,
                      left: 16,
                      child: Container(width: 24, height: 4, color: AppColors.teal),
                    ),
                    Positioned(
                      top: 16,
                      left: 16,
                      child: Container(width: 4, height: 24, color: AppColors.teal),
                    ),
                    Positioned(
                      top: 16,
                      right: 16,
                      child: Container(width: 24, height: 4, color: AppColors.teal),
                    ),
                    Positioned(
                      top: 16,
                      right: 16,
                      child: Container(width: 4, height: 24, color: AppColors.teal),
                    ),
                    Positioned(
                      bottom: 16,
                      left: 16,
                      child: Container(width: 24, height: 4, color: AppColors.teal),
                    ),
                    Positioned(
                      bottom: 16,
                      left: 16,
                      child: Container(width: 4, height: 24, color: AppColors.teal),
                    ),
                    Positioned(
                      bottom: 16,
                      right: 16,
                      child: Container(width: 24, height: 4, color: AppColors.teal),
                    ),
                    Positioned(
                      bottom: 16,
                      right: 16,
                      child: Container(width: 4, height: 24, color: AppColors.teal),
                    ),

                    // Laser Scanning Line Animation
                    AnimatedBuilder(
                      animation: _scannerAnimation,
                      builder: (context, child) {
                        return Positioned(
                          top: 260 * _scannerAnimation.value,
                          left: 20,
                          right: 20,
                          child: Container(
                            height: 3,
                            decoration: BoxDecoration(
                              color: AppColors.teal,
                              boxShadow: [
                                BoxShadow(
                                  color: AppColors.teal.withOpacity(0.8),
                                  blurRadius: 8,
                                  spreadRadius: 2,
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),

                    const Center(
                      child: Icon(
                        Icons.qr_code_scanner_rounded,
                        size: 90,
                        color: Colors.white24,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 28),

            // Quick QR Simulator Input Box
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF2C3132),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Nhập / Giả lập mã QR vé:',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (_scannedTickets.isNotEmpty)
                        TextButton(
                          onPressed: () {
                            setState(() => _scannedTickets.clear());
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text('Đã xóa lịch sử vé quét trùng.'),
                                duration: Duration(seconds: 1),
                              ),
                            );
                          },
                          child: const Text('Xóa bộ nhớ quét', style: TextStyle(color: AppColors.teal, fontSize: 11)),
                        ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _codeController,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            hintText: 'VD: 550e8400-e29b-41d4-a716-446655440000',
                            hintStyle: const TextStyle(color: Colors.white38, fontSize: 12),
                            filled: true,
                            fillColor: Colors.black26,
                            contentPadding: const EdgeInsets.symmetric(
                                horizontal: 14, vertical: 10),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: BorderSide.none,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      ElevatedButton(
                        onPressed: _isChecking
                            ? null
                            : () => _verifyQr(_codeController.text),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.teal,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 12),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                        child: Text(_isChecking ? 'Đang kiểm...' : 'Xác nhận'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Mẫu vé Supabase UUID & Quét thử nghiệm:',
                    style: TextStyle(color: Colors.white54, fontSize: 11),
                  ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      ActionChip(
                        label: const Text('Vé UUID #1'),
                        backgroundColor: Colors.white10,
                        labelStyle: const TextStyle(color: Colors.white, fontSize: 12),
                        onPressed: () {
                          const uuid = '550e8400-e29b-41d4-a716-446655440000';
                          _codeController.text = uuid;
                          _verifyQr(uuid);
                        },
                      ),
                      ActionChip(
                        label: const Text('Vé UUID #2'),
                        backgroundColor: Colors.white10,
                        labelStyle: const TextStyle(color: Colors.white, fontSize: 12),
                        onPressed: () {
                          const uuid = '8d2f3a4b-9999-4321-8888-abcdef123456';
                          _codeController.text = uuid;
                          _verifyQr(uuid);
                        },
                      ),
                      ActionChip(
                        label: const Text('Vé hỏng/Lỗi'),
                        backgroundColor: Colors.red.withOpacity(0.2),
                        labelStyle: const TextStyle(color: Colors.redAccent, fontSize: 12),
                        onPressed: () {
                          const invalidCode = 'INVALID-EXPIRED-999';
                          _codeController.text = invalidCode;
                          _verifyQr(invalidCode);
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
