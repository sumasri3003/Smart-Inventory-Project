import azure.functions as func
import logging
import json
from sqlalchemy import create_engine, text
import os
import certifi
from fpdf import FPDF
from azure.storage.blob import BlobServiceClient
from io import BytesIO
from datetime import datetime

# ==============================
#   ENVIRONMENT VARIABLES
# ==============================
DATABASE_URL = os.getenv("DATABASE_URL")
BLOB_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

ssl_args = {"ssl": {"ca": certifi.where()}}
engine = create_engine(DATABASE_URL, connect_args=ssl_args, pool_pre_ping=True)

blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
container_name = "invoices"
try:
    blob_service_client.create_container(container_name)
except Exception:
    pass  # Already exists

# ==============================
#   FUNCTION APP
# ==============================
app = func.FunctionApp()

# ==============================
#   1️⃣ PROCESS ORDER FUNCTION
# ==============================
@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="orders-queue",
    connection="SERVICE_BUS_CONNECTION_STRING"
)
def process_order(msg: func.ServiceBusMessage):
    logging.info("📦 Received new order event")

    try:
        body = msg.get_body().decode("utf-8")
        event = json.loads(body.replace("'", '"'))
        order_id = event.get("order_id")
        warehouse_id = event.get("warehouse_id")

        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO orders (ext_order_id, warehouse_id, status)
                    VALUES (:oid, :wid, 'created')
                """),
                {"oid": order_id, "wid": warehouse_id}
            )
            conn.commit()

        logging.info(f"✅ Order {order_id} inserted successfully into MySQL")

    except Exception as e:
        logging.error(f"❌ Error processing order: {str(e)}")
        raise


# ==============================
#   2️⃣ CONFIRM ORDER FUNCTION
# ==============================
class InvoicePDF(FPDF):
    def header(self):
        self.set_fill_color(44, 62, 80)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 15, "SMART INVENTORY SOLUTIONS PVT. LTD.", 0, 1, "C", fill=True)
        self.ln(4)

    def footer(self):
        self.set_y(-25)
        self.set_draw_color(180, 180, 180)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, "Thank you for your business!", 0, 1, "C")
        self.cell(0, 10, "Contact: support@smartinventory.com", 0, 0, "C")


@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="order-confirmation-queue",
    connection="SERVICE_BUS_CONNECTION_STRING",
)
def confirm_order(msg: func.ServiceBusMessage):
    logging.info("🚚 Received order confirmation event")

    try:
        body = msg.get_body().decode("utf-8")
        event = json.loads(body.replace("'", '"'))
        order_id = event["order_id"]

        # with engine.connect() as conn:
        #     conn.execute(
        #         text("UPDATE orders SET status='confirmed' WHERE order_id=:oid"),
        #         {"oid": order_id},
        #     )
        #     order = conn.execute(
        #         text("SELECT * FROM orders WHERE order_id=:oid"),
        #         {"oid": order_id},
        #     ).mappings().first()
        #     items = conn.execute(
        #         text("""
        #             SELECT product_id, quantity, price
        #             FROM order_items
        #             WHERE order_id=:oid
        #         """),
        #         {"oid": order_id},
        #     ).mappings().all()
        #     total_amount = sum(
        #         [float(i["quantity"]) * float(i["price"]) for i in items]
        #     )
        #     conn.commit()
        with engine.connect() as conn:
            # ✅ Update order status
            conn.execute(
                text("UPDATE orders SET status='confirmed' WHERE ext_order_id=:oid"),
                {"oid": order_id},
            )

            # ✅ Fetch order details
            order = conn.execute(
                text("SELECT * FROM orders WHERE ext_order_id=:oid"),
                {"oid": order_id},
            ).mappings().first()

            # 🧠 Safety check — handle missing order
            if order is None:
                logging.error(f"❌ No order found in DB for order_id={order_id}")
                return

            # ✅ Fetch order items
            items = conn.execute(
                text("""
                    SELECT product_id, quantity, price
                    FROM order_items
                    WHERE order_id=:oid
                """),
                {"oid": order_id},
            ).mappings().all()

            # 🧠 Safety check — handle missing items
            if not items:
                logging.warning(f"⚠️ No items found for order_id={order_id}")
                total_amount = 0
            else:
                total_amount = sum(
                    [float(i["quantity"]) * float(i["price"]) for i in items]
                )

            conn.commit()

        # --- Generate PDF Invoice ---
        pdf = InvoicePDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, f"Invoice #: INV-{order_id:04}", 0, 1, "R")
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, "R")
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Invoice Details", 0, 1, "L")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(100, 8, f"Order ID: {order_id}", 0, 1)
        pdf.cell(100, 8, f"Warehouse ID: {order['warehouse_id']}", 0, 1)
        pdf.cell(100, 8, "Customer: Sumasri", 0, 1)
        pdf.ln(8)

        pdf.set_fill_color(41, 128, 185)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(50, 10, "Product ID", 1, 0, "C", True)
        pdf.cell(40, 10, "Quantity", 1, 0, "C", True)
        pdf.cell(50, 10, "Price (INR)", 1, 0, "C", True)
        pdf.cell(50, 10, "Total (INR)", 1, 1, "C", True)

        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(0, 0, 0)
        fill = False
        for item in items:
            pdf.set_fill_color(245, 245, 245) if fill else pdf.set_fill_color(255, 255, 255)
            pid, qty, price = item["product_id"], item["quantity"], item["price"]
            line_total = float(qty) * float(price)
            pdf.cell(50, 10, str(pid), 1, 0, "C", fill)
            pdf.cell(40, 10, str(qty), 1, 0, "C", fill)
            pdf.cell(50, 10, f"{price:.2f}", 1, 0, "C", fill)
            pdf.cell(50, 10, f"INR {line_total:.2f}", 1, 1, "C", fill)
            fill = not fill
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(140, 10, "Grand Total", 1, 0, "R", fill=False)
        pdf.cell(50, 10, f"INR {total_amount:.2f}", 1, 1, "C", fill=False)

        pdf_data = bytes(pdf.output(dest="S"))
        pdf_stream = BytesIO(pdf_data)
        pdf_stream.seek(0)

        blob_name = f"invoice_order_{order_id}.pdf"
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_client.upload_blob(pdf_stream, overwrite=True)
        blob_url = blob_client.url

        with engine.connect() as conn:
            conn.execute(
                text("UPDATE orders SET invoice_blob=:url WHERE order_id=:oid"),
                {"url": blob_url, "oid": order_id},
            )
            conn.commit()

        logging.info(f"✅ Order {order_id} confirmed, invoice generated, and uploaded.")
        logging.info(f"📎 Invoice URL: {blob_url}")

    except Exception as e:
        logging.error(f"❌ Error in order confirmation: {str(e)}")
