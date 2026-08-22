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

    setState(() => _isChecking = true);
    try {
      final res = await widget.api.verifyTicket(cleanCode);
      if (mounted) {
        setState(() {
          _lastVerificationResult = {
            'success': true,
            'ticket_id': res['id'] ?? cleanCode,
            'student_name': res['student_name'] ?? 'Nguyễn Văn Sinh Viên',
            'student_code': res['student_code'] ?? 'B2012345',
            'route_name': res['route_name'] ?? 'Tuyến #1 - Khu II → Hòa An',
            'timestamp': DateTime.now().toString().substring(11, 16),
          };
        });
        _showResultDialog(true);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _lastVerificationResult = {
            'success': false,
            'error': e.toString(),
            'code': cleanCode,
          };
        });
        _showResultDialog(false);
      }
    } finally {
      if (mounted) setState(() => _isChecking = false);
    }
  }

  void _showResultDialog(bool isSuccess) {
    showModalBottomSheet(
      context: context,
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
                color: isSuccess
                    ? AppColors.teal.withOpacity(0.15)
                    : Colors.red.withOpacity(0.15),
              ),
              child: Icon(
                isSuccess ? Icons.check_circle_rounded : Icons.cancel_rounded,
                color: isSuccess ? AppColors.teal : Colors.red,
                size: 48,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              isSuccess ? 'XÁC NHẬN VÉ HỢP LỆ' : 'VÉ KHÔNG HỢP LỆ',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: isSuccess ? AppColors.teal : Colors.red,
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
            ] else ...[
              Text(
                'Mã QR "${_lastVerificationResult?['code'] ?? ''}" không tồn tại hoặc đã hết hạn sử dụng.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.black87),
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
                  backgroundColor: isSuccess ? AppColors.teal : Colors.grey[800],
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: const Text('Quét vé tiếp theo'),
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
                  const Text(
                    'Nhập / Giả lập mã QR vé:',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _codeController,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            hintText: 'VD: TICKET-101',
                            hintStyle: const TextStyle(color: Colors.white38),
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
                    'Mẫu quét thử nghiệm nhanh:',
                    style: TextStyle(color: Colors.white54, fontSize: 11),
                  ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 8,
                    children: [
                      ActionChip(
                        label: const Text('Mẫu vé #1'),
                        backgroundColor: Colors.white10,
                        labelStyle: const TextStyle(color: Colors.white),
                        onPressed: () {
                          _codeController.text = 'TICKET-TEST-001';
                          _verifyQr('TICKET-TEST-001');
                        },
                      ),
                      ActionChip(
                        label: const Text('Mẫu vé #2'),
                        backgroundColor: Colors.white10,
                        labelStyle: const TextStyle(color: Colors.white),
                        onPressed: () {
                          _codeController.text = 'TICKET-TEST-002';
                          _verifyQr('TICKET-TEST-002');
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
