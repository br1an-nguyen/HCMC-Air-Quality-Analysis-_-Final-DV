# Nguyên tắc và Phương pháp Trực quan hóa Dữ liệu

Tài liệu này hệ thống hóa các nguyên tắc, khái niệm và phương pháp luận về trực quan hóa dữ liệu, được thiết kế để hướng dẫn hệ thống trợ lý AI trong việc thiết kế và lập trình các biểu đồ trực quan hiệu quả và chính xác.

---

## Domain Knowledge: Các Khái niệm Cốt lõi
Hiểu rõ các thành phần cơ bản là điều kiện tiên quyết để tạo ra các biểu diễn dữ liệu có ý nghĩa.

* **Trực quan hóa Dữ liệu (Data Visualization):** Là một quá trình tính toán nhằm tạo ra các biểu diễn hình ảnh của dữ liệu để con người có thể hiểu, tin tưởng và quản lý các hệ thống phức tạp, đặc biệt là trong Trí tuệ nhân tạo có thể giải thích được (Explainable AI - XAI).
* **Dấu bản (Marks):** Là các yếu tố hình học cơ bản đóng vai trò là vật mang thông tin. Chúng được phân loại theo số chiều:
    * **0D:** Điểm (Points).
    * **1D:** Đường (Lines).
    * **2D:** Diện tích (Areas).
    * **3D:** Khối (Bodies).
* **Dấu bản vai trò là liên kết (Links):** Bao gồm sự bao chứa (containment) và sự kết nối (connection).
* **Biến thị giác (Visual Variables/Channels):** Là các thuộc tính điều khiển sự xuất hiện của các dấu bản, bao gồm: Vị trí (Position), Kích thước (chiều dài, diện tích), Hình dạng (Shape), Độ sáng (Lightness), Độ bão hòa (Saturation), Màu sắc (Hue), Hướng/Góc (Orientation/Angle), và Kết cấu (Texture).
* **Đặc tính của biến thị giác:**
    * **Tính lựa chọn (Selective):** Giúp người dùng dễ dàng tách biệt một đối tượng thay đổi khỏi các đối tượng khác.
    * **Tính liên kết (Associative):** Giúp nhóm các đối tượng giống nhau lại với nhau.
    * **Tính định lượng (Quantitative):** Hỗ trợ nhận diện mối quan hệ số học giữa các dấu bản.
    * **Tính thứ tự (Order):** Hỗ trợ việc đọc và hiểu các thứ bậc dữ liệu.
* **Ánh xạ (Mapping/Encoding):** Quá trình chuyển đổi các giá trị dữ liệu một cách hệ thống và logic thành các yếu tố thị giác.
    * **Ánh xạ 1-1:** Một biến dữ liệu tương ứng với một biến thị giác.
    * **Ánh xạ 1-n:** Sử dụng nhiều biến thị giác để biểu diễn một biến dữ liệu duy nhất nhằm tăng cường hiệu quả.
* **Thang đo (Scales):** Phải là ánh xạ một-đối-một giữa giá trị dữ liệu và giá trị thẩm mỹ.

---

## Mapping Rules: Quy tắc Ánh xạ Dữ liệu
Việc lựa chọn biến thị giác phải tuân theo đặc tính của loại dữ liệu để đảm bảo tính diễn đạt (Expressiveness) và tính hiệu quả (Effectiveness).

* **IF** dữ liệu là định lượng (Quantitative - ví dụ: 1.3, 5.7, 83):
    * **THEN** ưu tiên sử dụng các kênh theo thứ tự: Vị trí (Position) > Chiều dài (Length) > Góc (Angle) > Diện tích (Area) > Độ sáng (Lightness) > Độ bão hòa (Saturation).
* **IF** dữ liệu là thứ tự (Ordinal - ví dụ: tốt, trung bình, kém):
    * **THEN** ưu tiên sử dụng các kênh theo thứ tự: Vị trí (Position) > Độ sáng (Lightness) > Độ bão hòa (Saturation) > Màu sắc (Hue) > Chiều dài (Length) > Góc (Angle).
* **IF** dữ liệu là định danh/phân loại (Nominal/Categorical - ví dụ: chó, mèo, cá):
    * **THEN** ưu tiên sử dụng các kênh theo thứ tự: Vị trí (Position) > Hình dạng (Shape) > Màu sắc (Hue).
* **IF** cần biểu diễn thuộc tính thời gian (Temporal):
    * **THEN** ưu tiên sử dụng trục tọa độ thời gian và các biểu đồ đường để thể hiện xu hướng.
* **IF** biểu diễn mối quan hệ giữa hai biến định lượng:
    * **THEN** sử dụng Scatterplot (biểu đồ phân tán) với các điểm (points) được ánh xạ vào vị trí không gian ngang và dọc.
* **IF** cần thêm thuộc tính phân loại vào Scatterplot:
    * **THEN** sử dụng kênh Màu sắc (Hue) để phân biệt các nhóm dữ liệu.
* **IF** cần thêm thuộc tính định lượng thứ tư vào Scatterplot:
    * **THEN** sử dụng kênh Kích thước (Size) của điểm.

---

## Design Constraints: Ràng buộc Thiết kế và Khả năng Truy cập
Để đảm bảo biểu đồ chính xác và dễ hiểu, cần tuân thủ các ràng buộc nghiêm ngặt về nhận thức thị giác.

### Nguyên tắc Hiệu quả và Diễn đạt
> **[!IMPORTANT]**
> * **Nguyên tắc Diễn đạt (Expressiveness):** Phép mã hóa thị giác phải diễn đạt tất cả và CHỈ thông tin có trong thuộc tính tập dữ liệu. 
> * **Nguyên tắc Hiệu quả (Effectiveness):** Tầm quan trọng của thuộc tính dữ liệu phải tương xứng với độ nổi bật (Salience) của kênh thị giác được chọn.

### Độ chính xác trong nhận thức (Accuracy)
Dựa trên các thí nghiệm của Cleveland và McGill, khả năng nhận thức của con người đối với các kênh thị giác có độ sai số khác nhau:
* **Vị trí (Position):** Có độ chính xác cao nhất và tỷ lệ lỗi thấp nhất.
* **Diện tích hình chữ nhật và Góc (Angles):** Có độ lỗi trung bình.
* **Diện tích hình tròn (Circular areas):** Có độ lỗi cao nhất. Tránh sử dụng diện tích hình tròn để biểu diễn các giá trị định lượng quan trọng nếu cần độ chính xác cao.

### Tính phân biệt và Sự can thiệp (Discriminability & Interference)
* **Giới hạn phân biệt:** Các kênh như độ dày đường kẻ (linewidth) có số lượng "ngăn" (bins) phân biệt hữu hạn. Không nên sử dụng quá nhiều mức độ độ dày để tránh gây nhầm lẫn.
* **Sự can thiệp giữa các kênh (Separability vs. Integrality):**
    * **Tách biệt hoàn toàn:** Vị trí và Màu sắc (Position + Hue). Có thể sử dụng độc lập mà không gây nhiễu.
    * **Gây nhiễu nhẹ:** Kích thước và Màu sắc (Size + Hue).
    * **Gây nhiễu đáng kể:** Chiều rộng và Chiều cao (Width + Height). Khó nhận biết độc lập khi cả hai cùng thay đổi.
    * **Can thiệp nghiêm trọng:** Đỏ và Xanh lá (Red + Green).

### Hiệu ứng Nổi bật (Popout)
* Sử dụng các kênh thị giác độc lập (màu sắc, hình dạng, kích thước) để tạo hiệu ứng nổi bật tức thì thông qua xử lý song song (parallel processing) của não bộ.
* Tốc độ tìm kiếm đối tượng nổi bật phụ thuộc vào kênh được chọn và mức độ khác biệt so với các đối tượng gây nhiễu, nhưng KHÔNG phụ thuộc vào số lượng đối tượng gây nhiễu.
* **Cảnh báo:** Khi kết hợp nhiều kênh (ví dụ: tìm vòng tròn đỏ giữa các hình vuông đỏ và vòng tròn xanh), não bộ sẽ chuyển sang tìm kiếm tuần tự (serial search), làm giảm tốc độ xử lý tỷ lệ thuận với số lượng đối tượng.

### Ràng buộc về Màu sắc
* **Sequential (Tuần tự):** Sử dụng khi dữ liệu có thứ tự từ thấp đến cao.
* **Diverging (Phân kỳ):** Sử dụng khi dữ liệu có điểm trung tâm hoặc điểm trung hòa quan trọng.
* **Categorical (Phân loại):** Sử dụng các màu sắc (Hue) khác nhau để phân biệt các nhóm không có thứ tự.