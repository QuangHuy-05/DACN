# Lời báo cáo từng slide - Tổng kết Sprint 3 và kế hoạch Sprint 4

Kịch bản đi theo đúng thứ tự 24 slide trong `DACN_6_10_Group_23.pdf`. Các đoạn dưới mỗi tiêu đề là lời nói có thể sử dụng trực tiếp khi báo cáo. Thời lượng toàn bài dự kiến khoảng 23-28 phút, tùy tốc độ nói và thời gian giải thích bảng. Không cần đọc toàn bộ các ô trong bảng; lời báo cáo đã chọn các số liệu và kết luận cần nhấn mạnh.

Số liệu được đối chiếu với báo cáo Sprint 3 và kết quả đánh giá cuối ngày 05/10/2026. Các ghi chú biên tập cuối tài liệu không thuộc lời nói khi trình bày.

## Slide 01 - Tiêu đề nghiên cứu

**Thời lượng gợi ý: 30-40 giây.**

Kính thưa thầy, nhóm chúng em gồm Nguyễn Quang Tùng và Nguyễn Quang Huy xin trình bày báo cáo tổng kết Sprint 3 và kế hoạch Sprint 4 của đề tài “Chuẩn hóa và phân giải địa chỉ tiếng Việt qua thay đổi địa giới hành chính năm 2025”, dưới sự hướng dẫn của thầy Quản Thành Thơ.

Trong Sprint 3, nhóm tập trung xây dựng dữ liệu gán nhãn, hoàn thiện tài nguyên hành chính theo thời gian và thực nghiệm các mô hình tách thành phần địa chỉ. Bài báo cáo sẽ trình bày những kết quả đã có, các giới hạn còn tồn tại và nhiệm vụ dự kiến thực hiện trong Sprint 4.

## Slide 02 - Sprint 3: Phân công nhiệm vụ hai thành viên

**Thời lượng gợi ý: 45-60 giây.**

Trong Sprint 3, công việc được chia thành hai phần chính. Tùng phụ trách dữ liệu và tài nguyên: xây dựng hướng dẫn 11 nhãn, tổ chức gán nhãn trên Label Studio, kiểm tra ranh giới ký tự, quản lý chia tập và các ngoại lệ T1. Tùng cũng phụ trách xây dựng Gazetteer theo hai mốc thời gian, xác minh mã hành chính và đóng gói corpus phát hành.

Huy phụ trách mô hình và thực nghiệm: xây dựng giao thức đánh giá, xử lý ánh xạ từ văn bản gốc sang đầu vào mô hình, thực nghiệm HEUR-JW và CRF, huấn luyện hai mô hình dùng PhoBERT, sau đó đóng băng dự đoán và đánh giá ràng buộc động.

Hai thành viên cùng rà soát các cặp gần trùng, kiểm tra phạm vi chấm T1, đối chiếu số lượng nhãn và nghiệm thu báo cáo. Cách phối hợp này giúp nối các quyết định về dữ liệu với quá trình huấn luyện và chấm điểm.

## Slide 03 - Tổng quan kết quả Sprint 3: Ba trụ cột cốt lõi

**Thời lượng gợi ý: 60-75 giây.**

Kết quả Sprint 3 có thể tóm tắt qua ba nhóm. Thứ nhất là dữ liệu: nhóm đã phát hành corpus gồm 400 địa chỉ và 1.787 span, chia thành 240 mẫu train, 60 mẫu dev và 100 mẫu test. Tài nguyên hành chính có 11.962 mã đơn vị được xác minh, bao gồm mã của cả hệ cũ và hệ mới.

Thứ hai là kết quả T0, tách các đoạn thành phần trong địa chỉ, gọi là span. PhoBERT-CRF đạt F1 test 98,43%, cao nhất trong bốn mô hình được đánh giá. Mô hình đề xuất DYN đạt 98,21%. Cách chấm yêu cầu đúng cả nhãn và ranh giới của từng span.

Thứ ba là các giới hạn. DYN chưa nhận diện được lớp Lai trong T1; bốn nhãn T0 chưa có mẫu test; độ đồng thuận gán nhãn độc lập chưa được đo; và T2 chưa được thực nghiệm. Ràng buộc động cũng chưa cho thấy cải thiện, còn hai cấu hình Deepparse chưa chạy do điều khoản trọng số chưa rõ. Vì vậy, đây là kết quả hoàn thành một phần của Sprint 3, với các giới hạn được công khai.

## Slide 04 - Bài toán nghiên cứu, Schema và Corpus phát hành

**Thời lượng gợi ý: 60-75 giây.**

Sprint 3 tập trung vào hai nhiệm vụ. T0 xác định từng đoạn ký tự trong địa chỉ và gán một trong 11 nhãn, như số nhà, tên đường, phường xã hay tỉnh thành. T1 xác định địa chỉ thuộc hệ cũ, hệ mới hay hệ Lai, lấy mốc thay đổi hành chính ngày 01/07/2025. Một địa chỉ có thể được tách đúng thành phần nhưng vẫn chưa đủ bằng chứng để xác định hệ thời gian.

Corpus hiện có 400 mẫu. Trong 300 mẫu train và dev, có 87 mẫu quan sát trực tiếp, 81 mẫu dẫn xuất và 132 mẫu tổng hợp. Đối với 100 mẫu test, nguồn gốc khi tổng hợp vẫn chưa được xác minh đầy đủ. Viet-Receipt-VQA đang ở trạng thái HOLD và không được đưa vào corpus này.

Nhóm chia tập theo các khóa địa điểm đã đăng ký và rà soát 138 cặp gần trùng. Bằng chứng này xác nhận phạm vi kiểm toán group hiện có; chưa đủ để khẳng định các tập độc lập hoàn toàn về địa lý hoặc nguồn dữ liệu.

## Slide 05 - Chuẩn hóa dữ liệu: Gán nhãn, Rò rỉ và Ngoại lệ T1

**Thời lượng gợi ý: 60-75 giây.**

Quy trình gán nhãn bắt đầu từ các gợi ý do AI hỗ trợ. Người duyệt sau đó kiểm tra nội dung, ranh giới và hệ của từng span, rồi chốt nhãn phát hành. Vì có sử dụng gợi ý, nhóm mô tả dữ liệu là AI-assisted, human-reviewed. Hiện chưa có phép đo độ đồng thuận giữa hai người gán nhãn độc lập.

Để kiểm soát gần trùng giữa các tập, nhóm rà soát 138 cặp được phát hiện bằng độ tương đồng chuỗi. Các quyết định distinct đã được ghi nhận, nhưng độ giống nhau về chữ vẫn cần được xem cùng bằng chứng địa điểm và nguồn.

Riêng T1, trong 100 mẫu test chỉ có 64 mẫu đủ điều kiện chấm. Hai mươi mẫu không đủ bằng chứng xác định hệ và 16 mẫu thuộc các ngoại lệ đã được duyệt loại khỏi chấm T1. Việc loại này chỉ áp dụng cho T1: toàn bộ 100 địa chỉ và 446 span vẫn được giữ khi chấm T0. Nhờ đó, nhóm không làm thay đổi mẫu số T0 để tăng kết quả.

## Slide 06 - Gazetteer thời gian: Dual-snapshot và xác minh NSO

**Thời lượng gợi ý: 60-75 giây.**

Gazetteer là tài nguyên tra cứu tên, cấp đơn vị, đơn vị cha và mã hành chính theo thời gian. Phiên bản hiện tại có 14.149 thực thể, 10.597 cạnh ánh xạ nguyên tử và 187 alias đã kiểm chứng.

Nhóm đối chiếu hai snapshot của Tổng cục Thống kê: ngày 30/06/2025 cho hệ cũ và ngày 01/07/2025 cho hệ mới. Kết quả xác minh được 8.607 mã cũ và 3.355 mã mới, tổng cộng 11.962 mã đơn vị hành chính. Những mã chưa đủ bằng chứng được giữ ở trạng thái unresolved, gồm 2.187 mã cũ.

Tài nguyên cũng giữ nguyên 471 khóa cũ có nhiều đích, thay vì tự chọn một đích. Điều này cần thiết khi có chia tách hoặc quan hệ nhiều-nhiều. Hiện tra cứu chỉ được xác nhận ở hai ngày snapshot; chưa có hình học để phân định lãnh thổ, một số điều khoản tái phân phối nguồn còn chưa rõ, và T2 chưa được đánh giá đầu cuối. Số mã đã xác minh vì thế không phải độ chính xác của T2.

## Slide 07 - Ma trận mô hình: Thực nghiệm và Giới hạn bản quyền

**Thời lượng gợi ý: 50-65 giây.**

Nhóm đã chạy bốn mô hình để so sánh các mức độ phức tạp. HEUR-JW dùng luật và Gazetteer, hỗ trợ sáu nhãn T0 cùng phân loại hệ T1. CRF-INDEP dùng đặc trưng thủ công và mô hình chuỗi để xử lý 11 nhãn T0. PhoBERT-CRF bổ sung biểu diễn ngữ cảnh từ mô hình tiếng Việt tiền huấn luyện. DYN cũng dùng PhoBERT nhưng có thêm đầu phân loại T1 và ràng buộc động khi giải mã T0.

CRF và PhoBERT-CRF chưa có đầu T1, nên không có kết quả T1 cho hai mô hình này. Hai cấu hình Deepparse dự kiến dùng FastText vẫn ở trạng thái chưa thực nghiệm, do điều khoản của checkpoint trọng số chưa được công bố rõ ràng.

Như vậy, bảng kết quả chỉ có bốn mô hình đã chạy thật. Biến thể DYN tắt constraint xuất hiện ở phần sau là thí nghiệm trên cùng checkpoint, không phải một mô hình thứ năm được huấn luyện độc lập.

## Slide 08 - Phương pháp: Chuẩn hóa Tone Relocation và Kiến trúc Đa nhiệm

**Thời lượng gợi ý: 75-90 giây.**

Phương pháp có hai phần cần giải thích. Phần thứ nhất là giữ đúng ranh giới ký tự khi đưa văn bản tiếng Việt vào mô hình. Bộ tách từ có thể đổi cách đặt dấu, ví dụ “hoà” thành “hòa”, khiến chuỗi trung gian không khớp nguyên văn. Nếu ánh xạ không đúng, span dự đoán có thể bị trả về sai vị trí trên địa chỉ gốc.

Nhóm xử lý bằng Tone Relocation: chuẩn hóa đầu vào cho bộ tách từ, đồng thời lưu ánh xạ để đưa span về văn bản gốc. Kiểm tra với bộ xử lý thật đạt 300 trên 300 mẫu train/dev và giữ được toàn bộ 1.341 span. Đây là độ đúng của phép ánh xạ, không phải độ chính xác dự đoán của mô hình.

Phần thứ hai là kiến trúc DYN. PhoBERT được dùng chung cho hai đầu: T0 giải mã chuỗi BIO23 bằng CRF, còn T1 phân loại hệ cũ, mới hoặc Lai. Khi T1 đủ tin cậy là hệ mới, constraint hạn chế nhãn Quận/Huyện theo cấu trúc hành chính hai cấp. Lợi ích thực tế của cơ chế này được kiểm tra riêng bằng ablation.

## Slide 09 - Thực nghiệm: Lựa chọn bằng Dev và Đóng băng Dự đoán

**Thời lượng gợi ý: 60-75 giây.**

Hai mô hình dùng PhoBERT được huấn luyện trên môi trường Kaggle có hai GPU Tesla T4, với seed cố định là 42. Nhóm thử hai cấu hình c01 và c02 cho mỗi mô hình, rồi chọn bằng tập dev. PhoBERT-CRF đạt 93,33% và 93,89% F1 dev, nên chọn c02. DYN đạt 93,33% và 94,74%, cũng chọn c02.

Sau khi chốt cấu hình và checkpoint, mô hình chỉ nhận văn bản để sinh dự đoán test. Các file dự đoán được lưu và khóa bằng mã băm trước khi bộ chấm nạp nhãn test gold. Bộ chấm hoạt động riêng để đối chiếu dự đoán với đáp án.

Điểm chính là nhóm không dùng kết quả test để điều chỉnh tham số hay chọn lại checkpoint. Ngay cả khi thứ hạng dev và test khác nhau, lựa chọn đã chốt bằng dev vẫn được giữ. Do mới chạy một seed, độ ổn định giữa các lần huấn luyện còn cần đánh giá tiếp.

## Slide 10 - Kết quả T0 toàn schema và Cảnh báo Support nhãn

**Thời lượng gợi ý: 75-90 giây.**

T0 được chấm trên 100 địa chỉ và 446 span, theo exact-span matching: phải đúng cả đoạn ký tự và nhãn thì mới được tính đúng. HEUR-JW đạt F1 91,12%, CRF-INDEP đạt 90,76%, PhoBERT-CRF đạt 98,43%, còn DYN đạt 98,21%.

PhoBERT-CRF có 439 span đúng, bảy span dự đoán sai và bảy span bị thiếu. So với CRF độc lập, F1 tăng 7,67 điểm phần trăm trong thí nghiệm này. DYN có F1 dev cao hơn PhoBERT-CRF nhưng F1 test thấp hơn 0,22 điểm phần trăm. Nhóm báo cáo khác biệt này và giữ nguyên lựa chọn từ dev.

Tuy nhiên, năm nhãn phổ biến chiếm 431 trên 446 span, tức 96,64% support test. Vì vậy, micro F1 chủ yếu phản ánh nhóm nhãn này. Bốn nhãn không có span test nên chưa thể đánh giá; nhãn Khác chỉ có hai span và tất cả mô hình đều đạt F1 bằng không. Kết quả cao hiện tại chưa đủ để kết luận đã xử lý tốt toàn bộ 11 nhãn.

## Slide 11 - Đánh giá phân loại hệ T1: Thách thức nhận diện lớp Lai

**Thời lượng gợi ý: 60-75 giây.**

T1 được chấm riêng trên 64 mẫu đủ điều kiện. HEUR-JW phân loại đúng 59 mẫu, đạt accuracy 92,19% và macro F1 92,49%. DYN đúng 46 mẫu, đạt accuracy 71,88% và macro F1 56,26%.

Điểm yếu nổi bật của DYN là lớp Lai. Trong năm mẫu Lai, bốn mẫu bị dự đoán thành hệ cũ và một mẫu bị từ chối do thiếu độ tin cậy, nên F1 lớp này bằng không. Hiện tượng này cũng xuất hiện trên dev. Ngoài ra, DYN từ chối 12 trên 64 mẫu, khiến độ bao phủ còn 81,25%; HEUR chỉ từ chối ba mẫu.

Kết quả cho thấy khả năng tách span tốt của DYN chưa chuyển thành khả năng xác định hệ thời gian tốt. Cần tiếp tục kiểm tra dữ liệu lớp Lai, hiệu chuẩn độ tin cậy và cách sử dụng thông tin hành chính. Đây là các hướng nghiên cứu tiếp theo; kết quả hiện tại chưa xác định được nguyên nhân duy nhất. CRF và PhoBERT-CRF chưa triển khai T1 nên không tham gia so sánh này.

## Slide 12 - Paired Ablation: Đánh giá vai trò của Dynamic Constraint

**Thời lượng gợi ý: 60-75 giây.**

Để xác định tác động của constraint, nhóm so sánh hai lần giải mã dùng cùng checkpoint c02 của DYN, cùng bộ xử lý và cùng cấu hình độ tin cậy đã chọn trên dev. Khác biệt duy nhất là bật hoặc tắt constraint, nên không cần huấn luyện lại hai mô hình.

Khi bật constraint, T0 F1 đạt 98,21%; khi tắt đạt 98,43%. Constraint chỉ làm thay đổi một trong 100 địa chỉ, tương ứng hai span tuple khi tính một dự đoán cũ bị thay và một dự đoán mới được thêm. Thay đổi đó làm giảm 0,22 điểm phần trăm F1. Kết quả T1 không thay đổi.

Trong 12 mẫu gold hệ mới đủ điều kiện chấm, cả hai biến thể đều không có lỗi Quận/Huyện, nên chưa quan sát được lợi ích của constraint với loại lỗi này. Kết luận là constraint chưa cải thiện kết quả trong thiết lập hiện tại. Thí nghiệm này không đủ để giải thích bằng cơ chế attention hoặc khẳng định mọi ràng buộc hành chính đều không hữu ích.

## Slide 13 - Phân tích lỗi thực tế: Hai hiện tượng tiêu biểu

**Thời lượng gợi ý: 60-75 giây.**

Hai hiện tượng được chọn ở đây giúp giải thích các lỗi còn lại. Trường hợp thứ nhất là tên đường “Phố Bà Huyện Thanh Quan”. Từ “Huyện” nằm trong tên danh nhân nhưng cũng là một dấu hiệu hành chính. Trong báo cáo lỗi, HEUR đã dừng tên đường ở “Phố Bà”, cho thấy luật nhận diện tiền tố có thể cắt sai ranh giới khi thiếu ngữ cảnh. Hướng xử lý là bổ sung ví dụ tên đường dạng này và kiểm tra ngữ cảnh rộng hơn.

Trường hợp thứ hai là các cụm như “Khu Công Nghệ Cao”, có nhãn vàng là Khác nhưng bị mô hình gán sang nhãn khác. Train chỉ có ba span Khác, còn test có hai. Đây là dấu hiệu cần bổ sung dữ liệu và làm rõ hướng dẫn phân biệt các loại địa điểm; số mẫu quá nhỏ cũng khiến kết quả theo nhãn dễ biến động.

Hai ví dụ cho thấy phân tích lỗi cần xem cả ranh giới, cấp hành chính và độ phủ nhãn. Các hướng xử lý được dành cho dữ liệu Sprint 4, không dùng để sửa mô hình rồi chấm lại test Sprint 3.

## Slide 14 - Kết luận tổng kết kỹ thuật Sprint 3

**Thời lượng gợi ý: 50-65 giây.**

Tóm lại, Sprint 3 đã tạo được corpus 400 mẫu, quy trình gán nhãn có quyết định duyệt, tài nguyên hành chính theo hai snapshot và pipeline thực nghiệm có kiểm tra toàn vẹn artifact. Nhóm đã đánh giá bốn mô hình, trong đó PhoBERT-CRF đạt kết quả T0 cao nhất với F1 98,43%. Dự đoán được đóng băng trước bước chấm gold và các artifact trong phạm vi kiểm toán được giữ nguyên.

Các kết quả này vẫn đi kèm giới hạn: nguồn gốc 100 mẫu test chưa được xác minh đầy đủ khi tổng hợp; chưa đo độ đồng thuận gán nhãn độc lập; bốn nhãn T0 chưa có support test; DYN chưa nhận diện được lớp Lai; T2 và Deepparse chưa thực nghiệm. Kết quả huấn luyện cũng mới có một seed.

Vì vậy, nhóm xác định trạng thái Sprint 3 là hoàn thành một phần và còn bị chặn ở Deepparse. Phần tiếp theo trình bày chi tiết các bằng chứng trước khi chuyển sang phân công Sprint 4.

## Slide 15 - Danh mục tài liệu tham chiếu kỹ thuật

**Thời lượng gợi ý: 20-30 giây.**

Sau phần tổng kết, nhóm xin trình bày các chi tiết làm cơ sở cho kết quả vừa báo cáo. Các trang tiếp theo gồm định nghĩa 11 nhãn, kết quả theo từng nhãn, ma trận nhầm lẫn T1, tham số baseline, kiểm toán artifact, track năm trường và các lỗi kỹ thuật đã xử lý.

Các bảng này giúp thấy rõ mô hình làm tốt ở đâu và phần nào chưa đủ bằng chứng đánh giá. Em sẽ tập trung vào các điểm cần giải thích, rồi kết thúc bằng kế hoạch và phân công nhiệm vụ Sprint 4.

## Slide 16 - Chi tiết Schema 11 nhãn địa chỉ tiếng Việt

**Thời lượng gợi ý: 60-75 giây.**

Schema gồm 11 nhãn, có thể hiểu theo ba nhóm. Nhóm mô tả vị trí cụ thể gồm Số nhà, Tên đường, Ngõ/Hẻm và Tòa nhà/Căn hộ. Với Ngõ/Hẻm, cần giữ nguyên cụm, chẳng hạn “Ngõ 12”, thay vì chỉ lấy số rồi gán thành Số nhà.

Nhóm hành chính gồm Phường/Xã, Quận/Huyện và Tỉnh/Thành. Cấp đơn vị phải được xác định theo ngữ cảnh và hệ thời gian. Trong schema hiện tại, Quận/Huyện thuộc hệ cũ; hệ mới có hai cấp hành chính nên không thể giữ nhãn huyện theo cùng cấu trúc.

Nhóm bổ sung gồm Mốc định vị, Hướng đi, Ghi chú và Khác. Mốc định vị là nơi dùng làm tham chiếu; Hướng đi mô tả cách đến hoặc khoảng cách; Ghi chú bổ sung thông tin cho địa chỉ; Khác dành cho thành phần ngoài mười nhãn còn lại theo guideline.

Mục tiêu của schema là biểu diễn cả những thành phần thường bị bỏ qua khi chỉ tách năm trường. Tuy nhiên, độ phủ test hiện tại chưa đủ để đánh giá tất cả các nhãn bổ sung này.

## Slide 17 - Bảng F1 và Support chi tiết từng nhãn T0

**Thời lượng gợi ý: 60-75 giây.**

Bảng này cần được đọc cùng hai thông tin: F1 và số span của từng nhãn. Với các nhãn phổ biến, mô hình dùng PhoBERT có kết quả cao. PhoBERT-CRF đạt 99,5% F1 cho Tên đường và Tỉnh/Thành. DYN đạt 98,3% cho Phường/Xã và 95,6% cho Quận/Huyện.

DYN đạt 100% F1 ở Ngõ/Hẻm, nhưng test chỉ có 13 span thuộc nhãn này. Vì vậy, con số 100% chỉ mô tả kết quả trên các ví dụ đã chấm, chưa chứng minh mô hình đúng với mọi cách viết ngõ và hẻm.

Ở phía nhãn hiếm, Khác có ba span train và hai span test, F1 của cả bốn mô hình đều bằng không. Tòa nhà/Căn hộ, Mốc định vị, Hướng đi và Ghi chú không có span test, nên phải ghi chưa thể đánh giá, không coi là điểm không hay đã đạt yêu cầu. Tổng support là 1.057 span train, 284 span dev và 446 span test. Đây là cơ sở trực tiếp để ưu tiên bổ sung nhãn hiếm trong Sprint 4.

## Slide 18 - Ma trận nhầm lẫn chi tiết T1: PROPOSED-DYN

**Thời lượng gợi ý: 60-75 giây.**

Ma trận bên trái có hàng là nhãn vàng và cột là dự đoán. Trong 47 mẫu hệ cũ, DYN dự đoán đúng 36, nhầm một sang hệ mới và từ chối mười mẫu. Trong 12 mẫu hệ mới, mô hình đúng mười, nhầm một sang hệ cũ và từ chối một.

Với năm mẫu Lai, bốn bị gọi là hệ cũ và một bị từ chối. Mô hình không dự đoán lớp Lai cho mẫu nào trong 64 mẫu đủ điều kiện. Vì vậy, vấn đề không chỉ là số lượng mẫu từ chối mà còn là khả năng phân biệt một lớp cụ thể.

Bảng bên phải cho thấy F1 DYN ở hệ cũ là 81,82%, hệ mới là 86,96%, nhưng Lai bằng không, kéo macro F1 xuống 56,26%. HEUR đạt kết quả tốt hơn ở cả ba lớp trong tập này. Khi đánh giá T1, nhóm cần công bố đồng thời độ đúng, F1 từng lớp và độ bao phủ; chỉ nhìn độ đúng trên các mẫu đã chấp nhận sẽ bỏ qua các trường hợp mô hình từ chối.

## Slide 19 - Chi tiết tham số cấu hình Baseline: HEUR và CRF

**Thời lượng gợi ý: 50-65 giây.**

Với HEUR-JW, nhóm kết hợp tra cứu Gazetteer hai snapshot và độ tương đồng Jaro-Winkler. Sáu ngưỡng từ 0,82 đến 1,00 được thử trên dev, với margin cố định 0,02. Ngưỡng 0,86 cho F1 dev cao nhất là 88,01%, nên được chốt trước khi chạy test. HEUR hiện chỉ hỗ trợ sáu nhãn T0, vì vậy vẫn được chấm trong phạm vi toàn schema và chịu lỗi bỏ sót các nhãn chưa hỗ trợ.

Với CRF, nhóm sử dụng 23 trạng thái BIO: hai trạng thái cho mỗi nhãn và một trạng thái ngoài thực thể. Đặc trưng gồm dạng token, tiền tố và ngữ cảnh lân cận. Lưới tám cấu hình kết hợp hai độ rộng ngữ cảnh với bốn cặp tham số điều chuẩn. Cấu hình được chọn là context một, c1 bằng 0,1 và c2 bằng một, đạt 90,56% F1 dev.

Điểm cần nhấn mạnh là các baseline cũng được chọn bằng dev theo giao thức, giúp phép so sánh có cơ sở rõ ràng.

## Slide 20 - Bằng chứng tái lập và Kiểm toán mã băm SHA-256

**Thời lượng gợi ý: 50-65 giây.**

Slide này trình bày bằng chứng về tính toàn vẹn và khả năng kiểm tra lại thí nghiệm. Nhóm đối chiếu 2.352 mã băm của các file được bảo vệ. Bốn file nguồn lớn được theo dõi riêng bằng kích thước và thời gian sửa đổi. Các kiểm tra trong phạm vi đó đều đạt, cho thấy corpus và artifact đã đóng băng được giữ nguyên.

Môi trường Kaggle được xác nhận có hai Tesla T4. Việc tải checkpoint và kết quả về được kiểm đúng phiên bản cùng checksum, thay vì chỉ dựa vào trạng thái thành công của dịch vụ. Báo cáo nghiệm thu cuối cũng ghi 274 kiểm thử, gồm 266 đạt, tám bỏ qua có ghi nhận và không có ca thất bại; năm cấu hình kết quả đã được đối chiếu lại metric.

Đây là bằng chứng kiểm toán đã có tại mốc đóng Sprint 3. Mã băm xác nhận file không đổi; nó không tự chứng minh dữ liệu độc lập, mô hình tổng quát tốt hay kết quả ổn định qua nhiều seed. Những kiểm chứng đó cần các đánh giá riêng.

## Slide 21 - Đánh giá Track 5 trường truyền thống: 4.800 mẫu

**Thời lượng gợi ý: 50-65 giây.**

Ngoài T0 11 nhãn, nhóm đánh giá thêm track năm trường truyền thống, gồm Số nhà, Tên đường, Phường/Xã, Quận/Huyện và Tỉnh/Thành. Track có 4.800 dòng sau khi loại 100 mẫu holdout, nhằm kiểm tra khả năng tương thích với bài toán và dữ liệu phát triển trước đó.

F1 của HEUR là 81,99%, CRF là 85,59%, PhoBERT-CRF là 89,94%, DYN là 89,90% và DYN tắt constraint là 89,91%. PhoBERT-CRF tiếp tục cao nhất trong các cấu hình được so sánh, nhưng chênh lệch giữa các biến thể neural rất nhỏ.

Track này không phải tập test độc lập. Kiểm toán ghi nhận một mẫu đã thấy trong train và 4.799 mẫu chưa thấy theo registered site key; điều đó chưa chứng minh độc lập về nguồn hay địa lý. Cách biểu diễn và chấm năm trường cũng khác exact-span T0, nên không so trực tiếp F1 ở đây với 98,43% trên test T0 để kết luận mức suy giảm tổng quát hóa.

## Slide 22 - Bảng tổng hợp các trường hợp lỗi phân tích

**Thời lượng gợi ý: 60-75 giây.**

Bảng này tổng hợp các dạng lỗi để xác định hướng bổ sung dữ liệu. Trước hết là lỗi ranh giới: trong báo cáo gốc, HEUR cắt ngắn “Phố Bà Huyện Thanh Quan”, còn CRF có trường hợp gộp tiền tố ngõ với tên đường. Các lỗi này nhắc rằng nhận đúng một vài từ chưa đủ để xác định đúng toàn bộ span.

Nhóm thứ hai là nhầm nhãn hoặc cấp hành chính. PhoBERT-CRF có trường hợp gọi “Q 7” và “Thị xã Quế Võ” là Phường/Xã; DYN có trường hợp gọi “T. Bắc Ninh” là Quận/Huyện. Nhóm thứ ba là các cụm thuộc Khác, như “Khu Công Nghệ Cao”, bị gán sang nhãn khác khi dữ liệu nhãn này rất ít.

Dòng cuối về Tòa nhà/Căn hộ dùng để minh họa khoảng trống độ phủ: train chỉ có năm span, test không có span nào. Dòng này không được dùng như một ca lỗi test đã đo. Các dạng lỗi trên dẫn đến hai nhu cầu cho Sprint 4: bổ sung ví dụ có nguồn và chuẩn hóa quyết định gán nhãn, đồng thời giữ test Sprint 3 đóng băng.

## Slide 23 - Khó khăn kỹ thuật hạ tầng và giải pháp xử lý

**Thời lượng gợi ý: 60-75 giây.**

Trong quá trình triển khai, nhóm gặp bốn vướng mắc chính. Thứ nhất là tương thích môi trường và thư viện, được xử lý bằng runtime Python 3.11.16 cô lập cùng danh sách phiên bản để truy vết. Thứ hai là ánh xạ tiếng Việt khi bộ tách từ đổi cách đặt dấu. Tone Relocation đã giúp bảo toàn văn bản gốc và ranh giới nhãn, với 300 trên 300 mẫu train/dev kiểm tra đạt.

Thứ ba là giới hạn bộ nhớ khi Kaggle CLI tải checkpoint lớn qua một buffer. Nhóm chuyển sang tải từng khối một MiB, kiểm tra kích thước và mã băm, đồng thời giữ đúng phiên bản artifact cần tải. Điều này giúp xác minh file nhận được mà không phải nạp cả file vào RAM.

Thứ tư là điều khoản trọng số Deepparse chưa rõ. Vướng mắc này chưa được giải quyết bằng kỹ thuật, nên hai cấu hình DP vẫn chưa thực nghiệm. Nhóm giữ trạng thái đó trong báo cáo, không xem việc đã cài thư viện hoặc có adapter là bằng chứng đã chạy mô hình tiền huấn luyện.

## Slide 24 - Sprint 4: Định hướng trọng tâm và Phân công nhiệm vụ

**Thời lượng gợi ý: 75-90 giây.**

Từ các giới hạn đã ghi nhận, nhóm đề xuất ba ưu tiên cho Sprint 4. Một là bổ sung dữ liệu có nguồn cho bốn nhãn chưa có support test, nhãn Khác ít mẫu và địa chỉ Lai. Hai là tổ chức hai người gán nhãn mù độc lập, đo độ đồng thuận trước khi phân xử, dùng Cohen's kappa theo đơn vị đánh giá đã định nghĩa và F1 exact-span. Ba là chạy ba seed cố định 42, 1337 và 2025 để báo cáo trung bình cùng độ lệch chuẩn.

Tùng phụ trách đăng ký nguồn, kiểm soát group, quản lý gán nhãn và phát hành corpus Sprint 4. Huy phụ trách runner, hạ tầng đa seed, huấn luyện, đánh giá T0/T1 và ablation, sau đó tổng hợp Evaluation Card và bằng chứng kiểm toán.

Điều kiện bắt đầu là dữ liệu phải hoàn thành cổng phát hành và kiểm toán độc lập trước khi Huy huấn luyện. Việc chọn mô hình tiếp tục dùng dev; test Sprint 3 được giữ đóng băng và không dùng để tune. Đây là kế hoạch đề xuất, chưa phải kết quả đã thực hiện. Nhóm chúng em xin kết thúc báo cáo và cảm ơn thầy đã theo dõi.

---

## Ghi chú biên tập trước khi trình bày - Không đọc thành lời

Kịch bản trên bám nội dung chính của các slide và dùng báo cáo gốc để diễn đạt đúng những điểm chưa khớp. Bản PDF hiện tại còn các mục cần sửa để hình chiếu và lời nói thống nhất:

1. **Slide 03:** Có một đoạn nhận xét dài bắt đầu bằng “Nội dung cần sửa trước khi báo cáo” bị chèn vào cả file nguồn và PDF, gây tràn trang. Đoạn này không thuộc bài báo cáo và không được đưa vào lời nói.
2. **Slide 11:** Câu “head T1 đòi hỏi đồ thị tri thức hành chính” đang nêu một kết luận chưa được kiểm chứng. Lời báo cáo coi thông tin hành chính, dữ liệu Lai và hiệu chuẩn là các hướng cần thử tiếp.
3. **Slide 12:** Chưa có bằng chứng quy nguyên nhân kết quả ablation cho khả năng tự điều chỉnh của attention. Kết luận có căn cứ chỉ là constraint không cải thiện trong thiết lập đã đánh giá; 0/12 lỗi Quận/Huyện ở cả ON và OFF.
4. **Slide 13 và 22:** Cần sửa các ví dụ cho đúng báo cáo gốc. Lỗi “Phố Bà Huyện Thanh Quan” được ghi cho HEUR, với tên đường bị cắt ở “Phố Bà”; lỗi “T. Bắc Ninh” được ghi cho DYN với nhãn dự đoán Quận/Huyện. Không nên gán các hiện tượng này cho model khác khi chưa có error trace. Các chuỗi ghép đầy đủ và ví dụ Sky City cần nguồn/trace cụ thể nếu tiếp tục gọi là ca thực tế. Kịch bản chỉ dùng các hiện tượng đã có căn cứ và không coi Sky City là ca lỗi test.
5. **Slide 14:** Không gọi cả 400 mẫu là đã kiểm chứng nguồn, vì provenance tổng hợp của 100 mẫu test vẫn chưa xác minh đầy đủ.
6. **Slide 23:** MemoryError được ghi nhận khi tải checkpoint lớn bằng Kaggle CLI; nên thay “nạp dataset” bằng “tải checkpoint/artifact lớn”.
7. **Các slide có chênh lệch F1:** Dùng “điểm phần trăm” cho 7,67; 0,85 và 0,22 khi so sánh trực tiếp hai tỷ lệ. “Không có support” không đồng nghĩa “F1 bằng 0”; các nhãn không có span test phải ghi `NOT_EVALUABLE`.

Nguồn đối chiếu chính:

- [Bản trình chiếu hiện tại](DACN_6_10_Group_23.pdf)
- [Báo cáo Sprint 3 đầu cuối](../53_sprint3_end_to_end_report_20261005.md)
- [Báo cáo kết quả đánh giá cuối](../49_sprint3_final_results.md)
- [Coverage corpus phát hành](../../../../data/processed/annotation/sprint03/corpus_v1_release2/coverage.json)
- [Kiểm toán chia tập](../../../../data/processed/annotation/sprint03/corpus_v1_release2/split_audit_report.json)
