from langchain_core.tools import tool
import time
import random
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

@tool
def get_movies_and_schedules(location: str = "Cinestar Sinh Viên", date: str = "hôm nay") -> str:
    """
    Lấy danh sách các bộ phim đang chiếu và lịch chiếu tại rạp Cinestar Sinh Viên tại thời điểm hiện tại (runtime).
    """
    print(f"Bắt đầu lấy dữ liệu lịch chiếu thật từ Cinestar Sinh Viên...")
    movies_data = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("https://cinestar.com.vn/book-tickets/cf13e1ce-2c1f-4c73-8ce5-7ef65472db3c/")
            page.wait_for_load_state("networkidle")
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            for h3 in soup.find_all('h3'):
                title = h3.get_text().strip()
                if title in ["DANH SÁCH RẠP", "MÔ TẢ", "NỘI DUNG PHIM", "CHỌN LOẠI VÉ"]:
                    continue
                    
                container = h3.find_parent(class_=lambda c: c and ('film-item' in c or 'movie-item' in c or 'item' in c))
                if not container:
                    container = h3.find_parent('div')
                
                if container:
                    times = container.find_all(class_='movies-time-item')
                    if times:
                        time_list = list(dict.fromkeys([t.get_text().strip() for t in times]))
                        movies_data.append({
                            "movie_name": title,
                            "showtimes": time_list
                        })
        except Exception as e:
            print(f"Lỗi khi cào dữ liệu phim: {e}")
        finally:
            browser.close()

    if not movies_data:
        return "Không thể lấy được lịch chiếu hoặc hiện không có phim nào đang chiếu."

    movies_str = ""
    for m in movies_data[:5]:
        movies_str += f"- Phim: {m['movie_name']} | Các suất chiếu: {', '.join(m['showtimes'])}\n"
        
    return f"Danh sách phim và lịch chiếu:\n{movies_str}"

@tool
def get_available_seats(showtime_id: str, seat_type: str = "Standard", quantity: int = 1) -> str:
    """
    Kiểm tra sơ đồ ghế thật của rạp Cinestar Sinh Viên cho một suất chiếu cụ thể và trả về danh sách ghế còn trống.
    Args:
        showtime_id: Giờ chiếu cụ thể (ví dụ: "08:15" hoặc "19:00").
    """
    print(f"Bắt đầu kiểm tra ghế trống cho suất {showtime_id}...")
    available_seats = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("https://cinestar.com.vn/book-tickets/cf13e1ce-2c1f-4c73-8ce5-7ef65472db3c/")
            page.wait_for_load_state("networkidle")
            
            showtime_btn = page.locator(".movies-time-item").filter(has_text=showtime_id).first
            showtime_btn.wait_for(timeout=10000)
            showtime_btn.click()
            
            # Đợi một chút để hệ thống cập nhật lịch chiếu và hiển thị khu vực chọn vé
            page.wait_for_timeout(2000)
            
            # Tìm nút cộng vé của "Người lớn" hoặc "HSSV"
            # Thử tìm theo text để chính xác hơn hoặc dùng first nếu không có text
            plus_btn = page.locator(".count-plus").first
            plus_btn.wait_for(timeout=10000)
            plus_btn.click()
            
            # Đợi popup cảnh báo xuất hiện (nếu có)
            page.wait_for_timeout(1000)
            
            # Xử lý nút "Đồng ý" an toàn hơn
            try:
                agree_btn = page.locator("button, div").filter(has_text="Đồng ý").first
                if agree_btn.is_visible():
                    agree_btn.click()
                    page.wait_for_timeout(1000)
            except:
                print("Không tìm thấy hoặc không cần bấm nút Đồng ý")
                
            # Đợi sơ đồ ghế tải xong
            page.wait_for_selector(".seat-wr", timeout=10000)
            
            # Đọc DOM sơ đồ ghế
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            all_seats = soup.find_all(class_='seat-wr')
            print(f"Tìm thấy tổng cộng {len(all_seats)} ghế trong DOM.")
            
            for seat in all_seats:
                if 'booked' not in seat.get('class', []):
                    name_span = seat.find(class_='seat-name')
                    if name_span:
                        available_seats.append(name_span.get_text().strip())
                        
        except Exception as e:
            print(f"Lỗi khi kiểm tra ghế trống: {e}")
        finally:
            browser.close()

    if not available_seats:
        return f"Suất chiếu {showtime_id} hiện đã hết ghế hoặc không hiển thị được sơ đồ ghế."
        
    # Loại bỏ trùng lặp nếu có
    available_seats = list(dict.fromkeys(available_seats))
    return f"Suất chiếu {showtime_id} còn trống {len(available_seats)} ghế. Các ghế trống: {', '.join(available_seats[:20])}"

# Lưu trữ các trình duyệt đang chờ thanh toán
active_sessions = {}

# Tạo thư mục lưu vé nếu chưa có
import os
os.makedirs("app/static/tickets", exist_ok=True)

@tool
def checkout_and_get_payment_qr(showtime_id: str, seat_codes: list[str]) -> dict:
    """
    Thực hiện giữ ghế THẬT trên web Cinestar và tạo mã QR thanh toán.
    Giữ lại session để kiểm tra trạng thái sau.
    """
    print(f"Bắt đầu automation đặt ghế {seat_codes} cho suất {showtime_id}...")
    
    from playwright.sync_api import sync_playwright
    import time
    
    quantity = len(seat_codes)
    qr_url = f"https://img.vietqr.io/image/mbbank-0987654321-compact.png?amount={quantity * 55000}&addInfo=Cinestar%20{showtime_id}%20{','.join(seat_codes)}"
    
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    order_id = f"ORD_{int(time.time())}"
    success = False
    
    try:
        page.goto("https://cinestar.com.vn/book-tickets/cf13e1ce-2c1f-4c73-8ce5-7ef65472db3c/")
        page.wait_for_load_state("networkidle")
        
        # 1. Chọn suất chiếu
        showtime_btn = page.locator(".movies-time-item").filter(has_text=showtime_id).first
        showtime_btn.wait_for(timeout=10000)
        showtime_btn.click()
        page.wait_for_timeout(2000)
        
        # 2. Cộng số lượng vé bằng số ghế khách chọn
        plus_btn = page.locator(".count-plus").first
        plus_btn.wait_for(timeout=10000)
        for _ in range(quantity):
            plus_btn.click()
            page.wait_for_timeout(500)
            
        # 3. Xử lý popup "Đồng ý"
        page.wait_for_timeout(1000)
        try:
            agree_btn = page.locator("button, div").filter(has_text="Đồng ý").first
            if agree_btn.is_visible():
                agree_btn.click()
                page.wait_for_timeout(1000)
        except:
            pass
            
        # 4. Chọn từng ghế
        page.wait_for_selector(".seat-wr", timeout=10000)
        for code in seat_codes:
            seat_locator = page.locator(".seat-wr").filter(has_text=code).first
            if seat_locator.is_visible():
                seat_locator.click()
                page.wait_for_timeout(500)
                print(f"Đã click chọn ghế {code}")
            else:
                print(f"Không tìm thấy ghế {code} để click")
                
        # 5. Bấm nút Tiếp tục
        continue_btn = page.locator(".btn--pri").filter(has_text="Tiếp tục").first
        if continue_btn.is_visible():
            continue_btn.click()
            print("Đã bấm nút Tiếp tục (Bước 1: Chọn ghế)")
            page.wait_for_load_state("networkidle")
            
            # 1. Bypass trang Bắp Nước
            try:
                continue_concession = page.locator(".btn--pri").filter(has_text="Tiếp tục").first
                if continue_concession.is_visible():
                    continue_concession.click()
                    print("Đã bấm Tiếp tục (Bước 2: Bắp nước)")
                    page.wait_for_load_state("networkidle")
            except:
                pass
            
            # 2. Điền thông tin khách hàng
            try:
                page.wait_for_selector("input[name='fullname']", timeout=5000)
                page.fill("input[name='fullname']", "Khách Hàng AI")
                page.fill("input[name='phone']", "0901234567")
                page.fill("input[name='email']", "khachhang@example.com")
                
                page.locator(".btn--pri").filter(has_text="Thanh toán").first.click()
                print("Đã điền thông tin và bấm Thanh toán")
                page.wait_for_load_state("networkidle")
            except Exception as e:
                print(f"Lỗi điền thông tin: {e}")
            
            # 3. Chọn cổng thanh toán
            try:
                payment_method = page.locator("text=MoMo").first
                if payment_method.is_visible():
                    payment_method.click()
                    print("Đã chọn phương thức thanh toán MoMo")
                
                confirm_pay = page.locator("button, div").filter(has_text="Thanh toán").first
                if confirm_pay.is_visible():
                    confirm_pay.click()
                    print("Đã bấm xác nhận Thanh toán để chuyển trang")
                
                page.wait_for_url("**/*momo.vn*", timeout=15000)
                print("Đã chuyển hướng sang trang Momo")
            except Exception as e:
                print(f"Lỗi chọn cổng thanh toán hoặc không redirect được: {e}")
            
            # 4. Cào mã QR thật
            try:
                qr_locator = page.locator("img.qr-image-class, img[src*='generate-qr'], img[src*='qr'], img[src*='chart']").first
                qr_locator.wait_for(timeout=10000)
                real_qr_url = qr_locator.get_attribute("src")
                
                if real_qr_url:
                    print("LẤY THÀNH CÔNG QR THẬT CỔNG THANH TOÁN!")
                    qr_url = real_qr_url
            except Exception as e:
                print("Vẫn không lấy được QR từ cổng thanh toán, dùng fallback.")
            
            success = True
                
    except Exception as e:
        print(f"Lỗi khi automation đặt vé: {e}")
        success = False
        
    if success:
        # LƯU LẠI BROWSER VÀ PAGE ĐỂ DÙNG SAU (KHÔNG CLOSE)
        active_sessions[order_id] = {
            "browser": browser,
            "page": page,
            "playwright_context": p
        }
        print(f"Đã lưu session cho đơn hàng {order_id}")
    else:
        # Nếu lỗi thì đóng luôn
        try:
            browser.close()
            p.stop()
        except:
            pass
            
    total_price = quantity * 55000
    
    return {
        "order_id": order_id,
        "total_price": total_price,
        "qr_image_url": qr_url,
        "status": "pending_payment",
        "message": "Vui lòng quét mã QR để thanh toán. Sau khi quét xong, hãy nhắn 'Tôi đã thanh toán' để nhận vé."
    }

@tool
def check_order_status_and_get_ticket(order_id: str) -> dict:
    """
    Kiểm tra trạng thái đơn hàng và lấy vé nếu đã thanh toán.
    """
    session = active_sessions.get(order_id)
    if not session:
        return {"status": "error", "message": "Không tìm thấy phiên giao dịch hoặc phiên đã hết hạn."}
    
    page = session["page"]
    browser = session["browser"]
    p = session["playwright_context"]
    
    try:
        print(f"Đang kiểm tra trạng thái cho đơn hàng {order_id}...")
        # Đợi trang tự động nhảy sang trang thành công
        page.wait_for_url("**/*success*", timeout=10000) 
        print("Đã phát hiện chuyển hướng sang trang thành công!")
        
        # Chụp màn hình cái vé
        ticket_image_path = f"app/static/tickets/{order_id}.png"
        
        # Thử tìm element chứa vé để chụp, nếu không thấy thì chụp toàn bộ trang
        try:
            ticket_element = page.locator(".ticket-info-wrapper, .booking-success").first
            ticket_element.screenshot(path=ticket_image_path)
        except:
            page.screenshot(path=ticket_image_path)
            
        # Đóng browser và xóa session
        browser.close()
        p.stop()
        del active_sessions[order_id]
        
        return {
            "status": "paid",
            "message": "Thanh toán thành công! Đây là vé của bạn.",
            "ticket_qr_url": f"/static/tickets/{order_id}.png"
        }
    except Exception as e:
        print(f"Hệ thống chưa ghi nhận thanh toán: {e}")
        return {
            "status": "pending", 
            "message": "Hệ thống chưa ghi nhận thanh toán thành công. Bạn vui lòng hoàn tất thanh toán trên điện thoại hoặc thử lại sau vài giây."
        }
        # Không đóng browser ở đây để khách có thể thử lại!

movie_tools = [
    get_movies_and_schedules,
    get_available_seats,
    checkout_and_get_payment_qr,
    check_order_status_and_get_ticket
]
