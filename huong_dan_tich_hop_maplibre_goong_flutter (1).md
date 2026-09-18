# TÍCH HỢP MAPLIBRE TRÊN NỀN BẢN ĐỒ GOONG TRONG FLUTTER

## 1. Mục tiêu

Tích hợp **MapLibre** vào ứng dụng Flutter và sử dụng nền bản đồ/dịch vụ của **Goong Maps**.

AI thực hiện code cần đảm bảo các chức năng chính:

1. Hiển thị bản đồ Goong bằng MapLibre.
2. Hỗ trợ các style bản đồ:
   - Bản đồ cơ bản/highlight.
   - Bản đồ vệ tinh.
   - Có thể mở rộng sang các style khác nếu cần.
3. Hiển thị marker tại tọa độ latitude/longitude.
4. Di chuyển camera đến marker.
5. Tìm kiếm địa điểm:
   - Người dùng nhập tên địa chỉ.
   - Gọi Goong Autocomplete để lấy danh sách gợi ý.
   - Người dùng chọn một gợi ý.
   - Dùng `place_id` gọi Place Detail.
   - Lấy latitude/longitude.
   - Hiển thị marker và đưa camera đến vị trí đó.
6. Dẫn đường:
   - Có điểm đầu và điểm cuối.
   - Gọi Goong Directions.
   - Lấy route polyline.
   - Decode polyline.
   - Chuyển thành GeoJSON LineString.
   - Hiển thị tuyến đường trên MapLibre.
   - Có thể lấy distance/time từ response Directions để hiển thị cho người dùng.
7. Có khả năng xóa marker và tuyến đường cũ trước khi vẽ dữ liệu mới.

---

# 2. Yêu cầu chuẩn bị

Cần có:

- Flutter project đang hoạt động.
- Tài khoản Goong.
- Goong API Key.
- Map Tile Key nếu style bản đồ yêu cầu key riêng.

Tài liệu đăng ký và tạo key:

https://help.goong.io/kb/gioi-thieu-tong-quan/dang-ky-va-tao-key/dang-ky-tai-khoan-va-tao-key/

> **Lưu ý bảo mật:** Không hard-code API key trực tiếp vào source code production. Ưu tiên sử dụng biến môi trường, file cấu hình không commit lên Git hoặc cơ chế secret phù hợp.

---

# 3. Cài đặt package

Chạy:

```bash
flutter pub add maplibre_gl
```

Hoặc thêm vào `pubspec.yaml`:

```yaml
dependencies:
  maplibre_gl: ^0.19.0
```

Nếu project chưa có HTTP client:

```bash
flutter pub add http
```

Nếu sử dụng package decode polyline:

```bash
flutter pub add flutter_polyline_points
```

Sau đó chạy:

```bash
flutter pub get
```

> AI cần kiểm tra version package thực tế của project trước khi triển khai. Không tự ý thay đổi version nếu project đã có dependency tương thích.

---

# 4. Tích hợp MapLibre với Goong

## 4.1. Khởi tạo MapLibreMap

Ví dụ:

```dart
MapLibreMap(
  onMapCreated: _onMapCreated,
  onStyleLoadedCallback: _onStyleLoadedCallback,
  initialCameraPosition: CameraPosition(
    target: LatLng(
      21.03357551700003,
      105.81911236900004,
    ),
    zoom: 14.0,
  ),
)
```

Cần có biến controller:

```dart
MapLibreMapController? mapController;
```

Callback:

```dart
void _onMapCreated(MapLibreMapController controller) {
  mapController = controller;
}
```

Có thể dùng callback style:

```dart
void _onStyleLoadedCallback() {
  // Thực hiện các thao tác cần thiết sau khi style được load.
}
```

> **Quan trọng:** Marker, source và layer phụ thuộc vào MapLibre style. Nếu code cần thêm icon tùy chỉnh, phải đảm bảo icon đã được đăng ký/load trước khi sử dụng `iconImage`.

---

# 5. Cấu hình style bản đồ Goong

## 5.1. Bản đồ ít icon / highlight

Style URL:

```text
https://tiles.goong.io/assets/goong_map_highlight.json?api_key=<MAP_TILE_KEY>
```

## 5.2. Bản đồ vệ tinh

Style URL:

```text
https://tiles.goong.io/assets/goong_satellite.json?api_key=<MAP_TILE_KEY>
```

AI cần thiết kế code để có thể dễ dàng thay đổi style:

```dart
String mapStyle = 'https://tiles.goong.io/assets/goong_map_highlight.json?api_key=<MAP_TILE_KEY>';
```

Khi cần chuyển sang satellite:

```dart
String mapStyle = 'https://tiles.goong.io/assets/goong_satellite.json?api_key=<MAP_TILE_KEY>';
```

> Không ghi API key thật vào GitHub.

---

# 6. Cấu hình attribution

Nếu yêu cầu giao diện không hiển thị attribution button của MapLibre:

```dart
attributionButtonPosition: null,
```

AI cần kiểm tra yêu cầu attribution/license của Goong trước khi loại bỏ hoặc thay đổi attribution. Không được xóa thông tin attribution bắt buộc theo giấy phép/dịch vụ.

---

# 7. Camera

Camera ban đầu:

```dart
CameraPosition(
  target: LatLng(
    21.03357551700003,
    105.81911236900004,
  ),
  zoom: 14.0,
)
```

Di chuyển camera đến một tọa độ:

```dart
mapController!.animateCamera(
  CameraUpdate.newLatLng(destinationPoint),
);
```

Trong project thực tế, `destinationPoint` phải được lấy từ dữ liệu thật thay vì hard-code.

---

# 8. Marker

## 8.1. Biến quản lý marker

```dart
Symbol? _currentMarker;
LatLng? _destinationPoint;
```

## 8.2. Thêm marker tại điểm đích

```dart
Future<void> _addMarkerAtDestinationPoint() async {
  if (mapController == null) {
    print("Map controller is not initialized");
    return;
  }

  if (_destinationPoint == null) {
    print("Destination point is not set");
    return;
  }

  try {
    // Xóa marker hiện tại nếu có.
    if (_currentMarker != null) {
      await mapController!.removeSymbol(_currentMarker!);
    }

    // Thêm marker mới.
    _currentMarker = await mapController!.addSymbol(
      SymbolOptions(
        geometry: _destinationPoint!,
        iconImage: 'locationEnd',
        iconSize: 0.3,
      ),
    );

    // Di chuyển camera đến vị trí mới.
    await mapController!.animateCamera(
      CameraUpdate.newLatLng(_destinationPoint!),
    );
  } catch (e) {
    print("Error adding marker: $e");
  }
}
```

## 8.3. Yêu cầu dữ liệu

Marker chỉ cần:

```text
latitude
longitude
```

Chuyển thành:

```dart
LatLng(latitude, longitude)
```

> `iconImage: 'locationEnd'` chỉ hoạt động nếu icon `locationEnd` tồn tại trong style hoặc đã được thêm vào MapLibre. AI phải kiểm tra vấn đề này khi code.

## 8.4. Xóa marker

```dart
if (_currentMarker != null) {
  await mapController!.removeSymbol(_currentMarker!);
  _currentMarker = null;
}
```

---

# 9. Tìm kiếm địa điểm bằng Goong

Quy trình bắt buộc:

```text
User nhập địa chỉ
        ↓
Goong Autocomplete
        ↓
Danh sách predictions
        ↓
User chọn prediction
        ↓
Lấy place_id
        ↓
Goong Place Detail
        ↓
Lấy geometry.location.lat/lng
        ↓
Tạo LatLng
        ↓
Đặt marker
        ↓
Di chuyển camera
```

---

# 10. Goong Autocomplete API

Endpoint tham khảo:

```text
https://rsapi.goong.io/Place/AutoComplete
```

Ví dụ:

```dart
Future<void> _fetchData(String input) async {
  try {
    final url = Uri.parse(
      'https://rsapi.goong.io/Place/AutoComplete'
      '?location=21.013715429594125,105.79829597455202'
      '&input=${Uri.encodeComponent(input)}'
      '&api_key=<API_KEY>',
    );

    final response = await http.get(url);

    if (response.statusCode != 200) {
      throw Exception(
        'Autocomplete failed: ${response.statusCode}',
      );
    }

    final jsonResponse = jsonDecode(response.body);

    setState(() {
      places = jsonResponse['predictions'] as List<dynamic>;
      isShow = true;
      isHidden = true;
    });
  } catch (e) {
    print('Autocomplete error: $e');
  }
}
```

Goong trả về danh sách `predictions`.

Mỗi prediction thường chứa thông tin như:

```text
place_id
description
structured_formatting
```

Trong đó:

```text
place_id
```

được dùng cho bước Place Detail.

---

# 11. Tối ưu Autocomplete

**Không được gọi API cho mọi ký tự mà người dùng nhập mà không có giới hạn.**

Có thể triển khai một trong các chiến lược:

### Cách 1: Chỉ gọi khi >= 2 hoặc 3 ký tự

```dart
if (input.trim().length < 3) {
  return;
}
```

### Cách 2: Debounce

Chỉ gọi API sau khi người dùng ngừng nhập khoảng 300–1000 ms.

Ví dụ logic:

```text
User nhập
   ↓
Hủy timer cũ
   ↓
Tạo timer mới
   ↓
Nếu user không nhập tiếp
   ↓
Gọi Autocomplete
```

### Cách 3: Kết hợp cả hai

Khuyến nghị:

```text
< 3 ký tự → không gọi API
>= 3 ký tự → debounce
```

Lý do:

- Giảm số request.
- Giảm chi phí API.
- Giảm tải server.
- Trải nghiệm tìm kiếm ổn định hơn.

---

# 12. Goong Place Detail

Sau khi user chọn prediction, lấy:

```text
place_id
```

Gọi:

```text
https://rsapi.goong.io/place/detail
```

Ví dụ:

```dart
Future<void> _fetchDataPlaceDetail(String placeId) async {
  final url = Uri.parse(
    'https://rsapi.goong.io/place/detail'
    '?place_id=${Uri.encodeQueryComponent(placeId)}'
    '&api_key=<API_KEY>',
  );

  final response = await http.get(url);

  if (response.statusCode != 200) {
    throw Exception(
      'Place Detail failed: ${response.statusCode}',
    );
  }

  final jsonResponse = jsonDecode(response.body);

  final details = jsonResponse['result'];

  final location = details['geometry']['location'];

  setState(() {
    _destinationPoint = LatLng(
      (location['lat'] as num).toDouble(),
      (location['lng'] as num).toDouble(),
    );
  });

  await _addMarkerAtDestinationPoint();
}
```

Sau khi có tọa độ:

```dart
LatLng(
  details['geometry']['location']['lat'],
  details['geometry']['location']['lng'],
)
```

---

# 13. Cập nhật ô tìm kiếm

Prediction có thể chứa:

```text
description
structured_formatting.main_text
structured_formatting.secondary_text
```

Ví dụ:

```dart
_searchController.text = coordinate['description'];

mainText =
    coordinate['structured_formatting']['main_text'];

secondText =
    coordinate['structured_formatting']['secondary_text'];
```

AI cần xử lý null an toàn nếu các trường không tồn tại.

---

# 14. Dẫn đường bằng Goong Directions

Quy trình:

```text
Current Position
       +
Destination Point
       ↓
Goong Directions API
       ↓
routes[0]
       ↓
overview_polyline.points
       ↓
Decode polyline
       ↓
Danh sách Lat/Lng
       ↓
GeoJSON LineString
       ↓
MapLibre Source
       ↓
MapLibre Line Layer
```

---

# 15. Gọi Goong Directions API

Endpoint:

```text
https://rsapi.goong.io/Direction
```

Ví dụ:

```dart
Future<void> _fetchDataDirection() async {
  if (_currentPosition == null ||
      _destinationPoint == null) {
    return;
  }

  final origin =
      '${_currentPosition!.latitude},${_currentPosition!.longitude}';

  final destination =
      '${_destinationPoint!.latitude},${_destinationPoint!.longitude}';

  final url = Uri.parse(
    'https://rsapi.goong.io/Direction'
    '?origin=$origin'
    '&destination=$destination'
    '&vehicle=bike'
    '&api_key=<API_KEY>',
  );

  final response = await http.get(url);

  if (response.statusCode != 200) {
    throw Exception(
      'Direction failed: ${response.statusCode}',
    );
  }

  final jsonResponse = jsonDecode(response.body);

  final routes = jsonResponse['routes'];

  if (routes == null || routes.isEmpty) {
    throw Exception('No route found');
  }

  final route = routes[0];

  final encodedPolyline =
      route['overview_polyline']['points'];

  final result =
      polylinePoints.decodePolyline(encodedPolyline);

  final coordinates = result
      .map(
        (point) => [
          point.longitude,
          point.latitude,
        ],
      )
      .toList();

  _drawLine(coordinates);

  // Có thể lấy thêm distance/time nếu API response cung cấp.
}
```

> Nếu project yêu cầu phương tiện khác, thay `vehicle=bike` bằng vehicle phù hợp theo tài liệu Goong, ví dụ `car`, `taxi`, v.v.

---

# 16. Decode Polyline

Goong trả về route dưới dạng encoded polyline:

```dart
final route =
    jsonResponse['routes'][0]['overview_polyline']['points'];
```

Decode:

```dart
List<PointLatLng> result =
    polylinePoints.decodePolyline(route);
```

Chuyển thành coordinates của GeoJSON:

```dart
List<List<double>> coordinates = result
    .map(
      (point) => [
        point.longitude,
        point.latitude,
      ],
    )
    .toList();
```

**Quan trọng:**

GeoJSON sử dụng thứ tự:

```text
[longitude, latitude]
```

Không phải:

```text
[latitude, longitude]
```

---

# 17. Vẽ route bằng MapLibre

Sử dụng GeoJSON:

```dart
void _drawLine(List<List<double>> coordinates) {
  mapController?.removeLayer("line_layer");
  mapController?.removeSource("line_source");

  final geoJsonData = {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {
          "type": "LineString",
          "coordinates": coordinates,
        },
      },
    ],
  };

  mapController?.addSource(
    "line_source",
    GeojsonSourceProperties(
      data: geoJsonData,
    ),
  );

  mapController?.addLineLayer(
    "line_source",
    "line_layer",
    LineLayerProperties(
      lineColor: "#0000FF",
      lineWidth: 10,
      lineCap: "round",
      lineJoin: "round",
    ),
  );
}
```

---

# 18. Xóa route

Trước khi vẽ route mới:

```dart
mapController?.removeLayer("line_layer");
mapController?.removeSource("line_source");
```

Nên kiểm tra layer/source tồn tại nếu API version của MapLibre yêu cầu.

Có thể tạo helper:

```dart
Future<void> _clearRoute() async {
  try {
    await mapController?.removeLayer("line_layer");
  } catch (_) {}

  try {
    await mapController?.removeSource("line_source");
  } catch (_) {}
}
```

---

# 19. Kiến trúc code được khuyến nghị

AI **không nên dồn toàn bộ logic vào một Widget** nếu project đã có cấu trúc lớn.

Nên tách:

```text
lib/
├── features/
│   └── map/
│       ├── presentation/
│       │   └── map_screen.dart
│       ├── services/
│       │   ├── goong_places_service.dart
│       │   └── goong_direction_service.dart
│       ├── models/
│       │   ├── place_prediction.dart
│       │   └── direction_result.dart
│       └── widgets/
│           ├── map_view.dart
│           └── place_search.dart
│
└── core/
    └── config/
        └── api_config.dart
```

Nếu project hiện tại đã có architecture khác, AI phải **tôn trọng cấu trúc hiện có** thay vì tạo architecture mới không cần thiết.

---

# 20. Service layer

## Goong Places Service

Nên gom:

```text
Autocomplete
Place Detail
```

vào:

```text
GoongPlacesService
```

Ví dụ interface:

```dart
class GoongPlacesService {
  Future<List<dynamic>> autocomplete(String input) async {
    // ...
  }

  Future<LatLng> getPlaceDetail(String placeId) async {
    // ...
  }
}
```

## Goong Direction Service

Gom:

```text
Directions API
Decode polyline
Distance
Duration
Route coordinates
```

Ví dụ:

```dart
class GoongDirectionService {
  Future<DirectionResult> getDirection({
    required LatLng origin,
    required LatLng destination,
    required String vehicle,
  }) async {
    // ...
  }
}
```

---

# 21. Quản lý API Key

Không làm:

```dart
const apiKey = "AIza....";
```

hoặc:

```dart
const apiKey = "<REAL_SECRET>";
```

trong source code được commit lên Git.

Có thể thiết kế:

```dart
class ApiConfig {
  static const goongApiKey =
      String.fromEnvironment('GOONG_API_KEY');

  static const goongMapTileKey =
      String.fromEnvironment('GOONG_MAP_TILE_KEY');
}
```

Chạy Flutter:

```bash
flutter run \
  --dart-define=GOONG_API_KEY=YOUR_KEY \
  --dart-define=GOONG_MAP_TILE_KEY=YOUR_TILE_KEY
```

Đối với production, sử dụng phương án quản lý secret phù hợp với CI/CD và môi trường triển khai.

---

# 22. Error handling

AI phải xử lý tối thiểu các trường hợp:

### Map chưa khởi tạo

```dart
if (mapController == null) {
  return;
}
```

### Không có điểm đích

```dart
if (_destinationPoint == null) {
  return;
}
```

### API trả lỗi HTTP

```dart
if (response.statusCode != 200) {
  throw Exception(...);
}
```

### Autocomplete không có kết quả

```dart
if (predictions.isEmpty) {
  // Hiển thị "Không tìm thấy địa điểm".
}
```

### Place Detail không có geometry

Không được truy cập trực tiếp nếu dữ liệu null.

### Directions không có route

```dart
if (routes == null || routes.isEmpty) {
  // Hiển thị thông báo không tìm thấy tuyến đường.
}
```

### Polyline rỗng

Không được tạo LineString nếu không có coordinates.

---

# 23. Loading state

Trong khi gọi API cần có trạng thái:

```text
isSearching
isLoadingPlaceDetail
isLoadingDirection
```

Ví dụ:

```dart
bool isSearching = false;
bool isLoadingDirection = false;
```

Luồng:

```text
Start request
    ↓
isLoading = true
    ↓
API request
    ↓
Success/Error
    ↓
isLoading = false
```

Tránh để người dùng bấm nhiều lần tạo nhiều request trùng nhau.

---

# 24. Luồng chức năng hoàn chỉnh

## 24.1. Tìm kiếm

```text
1. User mở Map Screen
2. MapLibre load Goong style
3. User nhập địa chỉ
4. Kiểm tra input >= 3 ký tự
5. Debounce
6. Gọi Autocomplete
7. Hiển thị predictions
8. User chọn prediction
9. Lấy place_id
10. Gọi Place Detail
11. Lấy lat/lng
12. Tạo LatLng
13. Xóa marker cũ
14. Thêm marker mới
15. Animate camera đến marker
```

## 24.2. Dẫn đường

```text
1. Có currentPosition
2. Có destinationPoint
3. User yêu cầu dẫn đường
4. Gọi Goong Directions
5. Kiểm tra routes
6. Lấy routes[0]
7. Lấy overview_polyline.points
8. Decode polyline
9. Chuyển thành [longitude, latitude]
10. Xóa route cũ
11. Tạo GeoJSON
12. Add source
13. Add line layer
14. Hiển thị distance/time
```

---

# 25. Acceptance Criteria

AI chỉ hoàn thành task khi tất cả tiêu chí sau đạt:

## Map

- [ ] `maplibre_gl` được cài đặt.
- [ ] MapLibre hiển thị được Goong map style.
- [ ] Camera có thể di chuyển.
- [ ] Có thể thay đổi map style.
- [ ] Không commit API key thật.

## Marker

- [ ] Có thể tạo marker từ latitude/longitude.
- [ ] Marker cũ được xóa trước khi thêm marker mới.
- [ ] Camera di chuyển đến marker.
- [ ] Không crash khi controller chưa khởi tạo.

## Search

- [ ] Autocomplete hoạt động.
- [ ] Có debounce hoặc giới hạn số ký tự.
- [ ] Hiển thị danh sách predictions.
- [ ] Chọn prediction lấy được `place_id`.
- [ ] Place Detail trả về tọa độ.
- [ ] Marker được đặt tại tọa độ kết quả.
- [ ] Camera di chuyển đến kết quả.
- [ ] Có xử lý trường hợp không có kết quả/API lỗi.

## Directions

- [ ] Có origin.
- [ ] Có destination.
- [ ] Gọi Directions thành công.
- [ ] Decode được polyline.
- [ ] Coordinates đúng thứ tự `[longitude, latitude]`.
- [ ] Route được vẽ bằng GeoJSON.
- [ ] Route cũ được xóa trước khi vẽ route mới.
- [ ] Có xử lý không tìm thấy route.
- [ ] Có thể lấy distance/duration từ response nếu cần.

## Code quality

- [ ] Không hard-code secret.
- [ ] Không tạo duplicate API logic.
- [ ] Service/API logic được tách hợp lý.
- [ ] Có loading state.
- [ ] Có error handling.
- [ ] Không phá vỡ chức năng hiện tại của project.
- [ ] Chạy được `flutter analyze`.
- [ ] Chạy được project trên Android.
- [ ] Không tự ý nâng cấp/downgrade dependency nếu không cần thiết.

---

# 26. Các lỗi AI cần tránh

## Lỗi 1: Dùng latitude/longitude sai thứ tự

Sai:

```dart
[point.latitude, point.longitude]
```

Đúng với GeoJSON:

```dart
[point.longitude, point.latitude]
```

---

## Lỗi 2: Gọi Autocomplete liên tục

Không làm:

```text
m
ma
map
map l
map li
map lib
...
```

mỗi lần đều gọi API mà không debounce/giới hạn.

---

## Lỗi 3: Hard-code API key

Không commit:

```text
api_key=REAL_KEY
```

lên GitHub.

---

## Lỗi 4: Dùng marker icon chưa tồn tại

Nếu:

```dart
iconImage: 'locationEnd'
```

không được định nghĩa trong style hoặc chưa được add image, marker có thể không hiển thị.

AI phải kiểm tra cách MapLibre version hiện tại xử lý custom icon.

---

## Lỗi 5: Vẽ nhiều route chồng lên nhau

Trước khi vẽ:

```dart
removeLayer("line_layer");
removeSource("line_source");
```

---

## Lỗi 6: Truy cập API response mà không kiểm tra null

Không giả định:

```dart
jsonResponse['routes'][0]
```

luôn tồn tại.

Phải kiểm tra:

```text
response status
routes != null
routes.isNotEmpty
overview_polyline tồn tại
points không rỗng
```

---

# 27. Nhiệm vụ dành cho AI code agent

AI cần thực hiện theo thứ tự:

### Bước 1 — Phân tích project

- Đọc `pubspec.yaml`.
- Kiểm tra Flutter/Dart version.
- Kiểm tra architecture hiện tại.
- Tìm màn hình map hiện có nếu có.
- Tìm các service/API hiện có.
- Tìm vị trí cấu hình API key.
- Không tạo file trùng chức năng.

### Bước 2 — Cài dependency

Đảm bảo project có:

```text
maplibre_gl
http
flutter_polyline_points
```

Chỉ thêm package còn thiếu.

### Bước 3 — Tích hợp MapLibre

- Tạo/điều chỉnh MapLibre map.
- Load Goong style.
- Khởi tạo controller.
- Xử lý style loaded.

### Bước 4 — Marker

- Tạo marker destination.
- Xóa marker cũ.
- Animate camera.
- Kiểm tra icon.

### Bước 5 — Search

- Implement Autocomplete.
- Debounce.
- Hiển thị predictions.
- Implement Place Detail.
- Cập nhật destination.
- Thêm marker.

### Bước 6 — Directions

- Implement Directions service.
- Decode polyline.
- Tạo GeoJSON.
- Add source/layer.
- Xóa route cũ.
- Hiển thị route.

### Bước 7 — Error/loading state

Hoàn thiện:

```text
loading
error
empty result
controller null
invalid response
```

### Bước 8 — Kiểm thử

Chạy:

```bash
flutter pub get
flutter analyze
flutter test
```

Nếu project không có test:

```text
Không tự ý tạo một hệ thống test lớn.
```

Có thể kiểm tra thủ công Android:

```bash
flutter run
```

---

# 28. Kết quả cuối cùng cần đạt

Ứng dụng Flutter phải có luồng sử dụng:

```text
┌──────────────────────────────┐
│        GOONG MAP             │
│                              │
│   🔍 Tìm kiếm địa điểm       │
│                              │
│            📍                │
│          /                   │
│        / route               │
│      /                       │
│   🚌 Current Position       │
│                              │
└──────────────────────────────┘
          │
          ├── Search
          │      ↓
          │  Autocomplete
          │      ↓
          │  Place Detail
          │      ↓
          │  Destination Marker
          │
          └── Directions
                 ↓
             Goong Direction
                 ↓
             Decode Polyline
                 ↓
             GeoJSON
                 ↓
             MapLibre Line Layer
```

**Mục tiêu cuối:** Người dùng có thể mở bản đồ Goong trong Flutter, tìm kiếm một địa điểm, chọn kết quả để đặt marker và sau đó yêu cầu dẫn đường từ vị trí hiện tại đến điểm đã chọn; tuyến đường được lấy từ Goong Directions và hiển thị trực tiếp trên MapLibre.
