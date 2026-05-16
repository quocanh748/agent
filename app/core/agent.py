from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from app.core.tools import movie_tools
from langchain_core.messages import SystemMessage

# Khởi tạo model
# Nên dùng qwen2.5:4b hoặc cao hơn để gọi tool ổn định
llm = ChatOllama(model="qwen3.5:4b", temperature=0.0)

# Tạo memory để lưu trữ chat history
memory = MemorySaver()

# Tạo LangGraph agent
# create_react_agent tự động tạo đồ thị với các node: agent và tools
langgraph_agent = create_react_agent(
    llm, 
    tools=movie_tools, 
    prompt="""Bạn là trợ lý AI chuyên nghiệp của rạp chiếu phim Cinestar Sinh Viên.
Nhiệm vụ của bạn là tư vấn phim, cung cấp lịch chiếu và hỗ trợ khách hàng đặt vé xem phim.
Bạn CÓ THỂ SỬ DỤNG CÁC CÔNG CỤ (TOOLS) để cào dữ liệu thực tế:
- Để lấy danh sách phim và lịch chiếu, GỌI TOOL: get_movies_and_schedules.
- Để kiểm tra ghế trống, GỌI TOOL: get_available_seats.
- Để tạo đơn hàng và lấy mã QR thanh toán, GỌI TOOL: checkout_and_get_payment_qr.
- Để kiểm tra trạng thái đơn hàng, GỌI TOOL: check_order_status_and_get_ticket.

HÃY LUÔN SỬ DỤNG TOOL KHI NGƯỜI DÙNG HỎI LỊCH CHIẾU HOẶC YÊU CẦU ĐẶT VÉ!
Hãy luôn trả lời bằng tiếng Việt một cách lịch sự và tự nhiên. KHÔNG BAO GIỜ bịa đặt lịch chiếu.

ĐẶC BIỆT: Khi checkout_and_get_payment_qr trả về link ảnh QR (qr_image_url), bạn PHẢI hiển thị nó trong đoạn chat bằng cú pháp markdown: ![QR Code](link_ảnh).""",
    checkpointer=memory
)

def ask_agent(question: str, session_id: str = "default_user"):
    """
    Hàm gọi agent với câu hỏi và session_id để giữ lịch sử chat.
    """
    config = {"configurable": {"thread_id": session_id}}
    
    # LangGraph agent nhận vào một dict chứa danh sách messages
    # Chúng ta truyền message mới vào
    inputs = {"messages": [("user", question)]}
    
    # Thực thi agent
    response = langgraph_agent.invoke(inputs, config=config)
    
    # Lấy message cuối cùng (là response của AI)
    return response["messages"][-1].content
