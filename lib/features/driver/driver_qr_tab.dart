import 'dart:async';

import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';

class DriverQrTab extends StatefulWidget {
  const DriverQrTab({super.key, required this.api});

  final ApiService api;

  @override
  State<DriverQrTab> createState() => _DriverQrTabState();
}

class _DriverQrTabState extends State<DriverQrTab> {
  final TextEditingController _codeController = TextEditingController();
  final MobileScannerController _scannerController = MobileScannerController(
    facing: CameraFacing.back,
    detectionSpeed: DetectionSpeed.noDuplicates,
    formats: const [BarcodeFormat.qrCode],
  );

  bool _isChecking = false;
  Map<String, dynamic>? _lastVerificationResult;

  @override
  void dispose() {
    _codeController.dispose();
    unawaited(_scannerController.dispose());
    super.dispose();
  }

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_isChecking) return;
    for (final barcode in capture.barcodes) {
      final value = barcode.rawValue?.trim();
      if (value != null && value.isNotEmpty) {
        await _verifyQr(value);
        return;
      }
    }
  }

  Future<void> _verifyQr(String code) async {
    final cleanCode = code.trim();
    if (cleanCode.isEmpty || _isChecking) return;

    setState(() => _isChecking = true);
    try {
      await _scannerController.stop();
    } catch (_) {
      // Continue verification if the scanner was already stopped by lifecycle.
    }

    var resultStatus = 'invalid';
    try {
      final res = await widget.api.verifyTicket(cleanCode);
      if (!mounted) return;
      resultStatus = 'success';
      setState(() {
        _lastVerificationResult = {
          'student_name': res['student_name']?.toString() ?? 'Không rõ sinh viên',
          'student_code': res['student_code']?.toString() ?? '—',
          'route_name': res['route_name']?.toString() ?? '—',
          'timestamp': _currentTime(),
        };
      });
    } catch (e) {
      if (!mounted) return;
      final errorMessage = e.toString().replaceFirst('Exception: ', '');
      setState(() {
        _lastVerificationResult = {
          'code': cleanCode,
          'error': errorMessage,
          'timestamp': _currentTime(),
        };
      });
    }

    try {
      if (mounted) await _showResultDialog(resultStatus);
    } finally {
      if (mounted) {
        setState(() => _isChecking = false);
        try {
          await _scannerController.start();
        } catch (_) {
          // The manual input remains available if camera access is unavailable.
        }
      }
    }
  }

  String _currentTime() {
    final now = DateTime.now();
    return '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
  }

  Future<void> _showResultDialog(String status) async {
    final isSuccess = status == 'success';
    final themeColor = isSuccess ? AppColors.teal : Colors.red;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (sheetContext) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isSuccess ? Icons.check_circle_rounded : Icons.cancel_rounded,
              color: themeColor,
              size: 60,
            ),
            const SizedBox(height: 12),
            Text(
              isSuccess ? 'XÁC NHẬN VÉ HỢP LỆ' : 'KHÔNG THỂ XÁC NHẬN VÉ',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: themeColor),
            ),
            const SizedBox(height: 14),
            if (isSuccess && _lastVerificationResult != null)
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFF0F4F4),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  children: [
                    _infoRow('Sinh viên:', '${_lastVerificationResult!['student_name']} (${_lastVerificationResult!['student_code']})'),
                    const SizedBox(height: 7),
                    _infoRow('Tuyến xe:', _lastVerificationResult!['route_name'].toString()),
                    const SizedBox(height: 7),
                    _infoRow('Thời gian:', _lastVerificationResult!['timestamp'].toString()),
                  ],
                ),
              )
            else if (_lastVerificationResult != null)
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFF0F0),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Column(
                  children: [
                    Text(
                      _lastVerificationResult!['error']?.toString() ?? 'Vé không hợp lệ.',
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.red, fontSize: 13, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 8),
                    _infoRow('Mã QR:', _lastVerificationResult!['code']?.toString() ?? '—'),
                  ],
                ),
              ),
            const SizedBox(height: 18),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: () {
                  Navigator.pop(sheetContext);
                  _codeController.clear();
                },
                style: FilledButton.styleFrom(
                  backgroundColor: themeColor,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('Quét vé tiếp theo', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(color: Colors.grey, fontSize: 13)),
        const SizedBox(width: 12),
        Flexible(
          child: Text(value, textAlign: TextAlign.right,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
        ),
      ],
    );
  }

  Widget _cameraError(BuildContext context, MobileScannerException error) {
    final permissionDenied = error.errorCode == MobileScannerErrorCode.permissionDenied;
    final message = permissionDenied
        ? 'Ứng dụng chưa được cấp quyền camera. Hãy cấp quyền trong Cài đặt để quét vé.'
        : error.errorCode == MobileScannerErrorCode.unsupported
            ? 'Thiết bị hoặc nền tảng này không hỗ trợ camera scanner.'
            : 'Không mở được camera. Bạn có thể nhập mã vé bên dưới.';
    return ColoredBox(
      color: const Color(0xFF202526),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.no_photography_outlined, color: Colors.white70, size: 40),
              const SizedBox(height: 12),
              Text(message, textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white70, fontSize: 13)),
              const SizedBox(height: 10),
              TextButton.icon(
                onPressed: () => _scannerController.start(),
                icon: const Icon(Icons.refresh),
                label: const Text('Thử mở camera lại'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF181C1D),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text('Quét mã QR vé Sinh viên', style: TextStyle(color: Colors.white)),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const Text(
              'Hướng camera về phía mã QR trên vé sinh viên',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white70, fontSize: 14),
            ),
            const SizedBox(height: 20),
            Center(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(24),
                child: SizedBox(
                  width: 300,
                  height: 300,
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      MobileScanner(
                        controller: _scannerController,
                        onDetect: _onDetect,
                        errorBuilder: _cameraError,
                      ),
                      IgnorePointer(
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            border: Border.all(color: AppColors.teal, width: 3),
                            borderRadius: BorderRadius.circular(24),
                          ),
                          child: const Center(
                            child: Icon(Icons.qr_code_scanner_rounded, size: 68, color: Colors.white54),
                          ),
                        ),
                      ),
                      if (_isChecking)
                        const ColoredBox(
                          color: Color(0x88000000),
                          child: Center(child: CircularProgressIndicator(color: AppColors.teal)),
                        ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF2C3132),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Nhập mã vé nếu không quét được camera:',
                      style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _codeController,
                          enabled: !_isChecking,
                          style: const TextStyle(color: Colors.white),
                          textInputAction: TextInputAction.done,
                          onSubmitted: _isChecking ? null : _verifyQr,
                          decoration: InputDecoration(
                            hintText: 'Mã QR trên vé, ví dụ BUS-ABC123',
                            hintStyle: const TextStyle(color: Colors.white38, fontSize: 12),
                            filled: true,
                            fillColor: Colors.black26,
                            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: BorderSide.none,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      FilledButton(
                        onPressed: _isChecking ? null : () => _verifyQr(_codeController.text),
                        style: FilledButton.styleFrom(
                          backgroundColor: AppColors.teal,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                        child: Text(_isChecking ? 'Đang kiểm...' : 'Xác nhận'),
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
