"""
database/models.py
==================
SQLAlchemy ORM models defining all 9 Olist e-commerce tables with proper
column types, primary keys, and foreign-key relationships that mirror the
CSV schema discovered during workspace inspection.
"""

from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship

# ---------------------------------------------------------------------------
# Base class that all ORM models inherit from -- used by create_all() later.
# ---------------------------------------------------------------------------
Base = declarative_base()


# ===========================================================================
# GEOLOCATION -- zip-code-level lat/lng coordinates for Brazil
# ===========================================================================
class Geolocation(Base):
    __tablename__ = "geolocation"

    # Composite natural key (zip + lat + lng) but we use a surrogate PK
    # because the raw data has many duplicates per zip code.
    id = Column(Integer, primary_key=True, autoincrement=True)
    geolocation_zip_code_prefix = Column(String(10), index=True)
    geolocation_lat = Column(Float)
    geolocation_lng = Column(Float)
    geolocation_city = Column(String(255))
    geolocation_state = Column(String(5))


# ===========================================================================
# CUSTOMERS -- unique buyers on the platform
# ===========================================================================
class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(50), primary_key=True)
    customer_unique_id = Column(String(50), index=True)
    customer_zip_code_prefix = Column(String(10))
    customer_city = Column(String(255))
    customer_state = Column(String(5))

    # One customer can place many orders
    orders = relationship("Order", back_populates="customer")


# ===========================================================================
# SELLERS -- third-party merchants fulfilling orders
# ===========================================================================
class Seller(Base):
    __tablename__ = "sellers"

    seller_id = Column(String(50), primary_key=True)
    seller_zip_code_prefix = Column(String(10))
    seller_city = Column(String(255))
    seller_state = Column(String(5))

    # One seller can appear in many order items
    order_items = relationship("OrderItem", back_populates="seller")


# ===========================================================================
# PRODUCT CATEGORY TRANSLATION -- Portuguese -> English category names
# ===========================================================================
class ProductCategoryTranslation(Base):
    __tablename__ = "product_category_translation"

    product_category_name = Column(String(255), primary_key=True)
    product_category_name_english = Column(String(255))


# ===========================================================================
# PRODUCTS -- items available for purchase
# ===========================================================================
class Product(Base):
    __tablename__ = "products"

    product_id = Column(String(50), primary_key=True)
    product_category_name = Column(
        String(255),
        nullable=True,
    )
    product_name_lenght = Column(Integer, nullable=True)       # sic -- original typo
    product_description_lenght = Column(Integer, nullable=True) # sic
    product_photos_qty = Column(Integer, nullable=True)
    product_weight_g = Column(Float, nullable=True)
    product_length_cm = Column(Float, nullable=True)
    product_height_cm = Column(Float, nullable=True)
    product_width_cm = Column(Float, nullable=True)

    # Relationships
    order_items = relationship("OrderItem", back_populates="product")


# ===========================================================================
# ORDERS -- each row is one purchase transaction
# ===========================================================================
class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String(50), primary_key=True)
    customer_id = Column(
        String(50),
        ForeignKey("customers.customer_id"),
    )
    order_status = Column(String(30))
    order_purchase_timestamp = Column(DateTime, nullable=True)
    order_approved_at = Column(DateTime, nullable=True)
    order_delivered_carrier_date = Column(DateTime, nullable=True)
    order_delivered_customer_date = Column(DateTime, nullable=True)
    order_estimated_delivery_date = Column(DateTime, nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")
    payments = relationship("OrderPayment", back_populates="order")
    reviews = relationship("OrderReview", back_populates="order")


# ===========================================================================
# ORDER ITEMS -- line items linking orders <-> products <-> sellers
# ===========================================================================
class OrderItem(Base):
    __tablename__ = "order_items"

    # Composite PK: (order_id, order_item_id)
    order_id = Column(
        String(50),
        ForeignKey("orders.order_id"),
        primary_key=True,
    )
    order_item_id = Column(Integer, primary_key=True)
    product_id = Column(
        String(50),
        ForeignKey("products.product_id"),
    )
    seller_id = Column(
        String(50),
        ForeignKey("sellers.seller_id"),
    )
    shipping_limit_date = Column(DateTime, nullable=True)
    price = Column(Float)
    freight_value = Column(Float)

    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    seller = relationship("Seller", back_populates="order_items")


# ===========================================================================
# ORDER PAYMENTS -- one or more payment records per order
# ===========================================================================
class OrderPayment(Base):
    __tablename__ = "order_payments"

    # Composite PK: (order_id, payment_sequential)
    order_id = Column(
        String(50),
        ForeignKey("orders.order_id"),
        primary_key=True,
    )
    payment_sequential = Column(Integer, primary_key=True)
    payment_type = Column(String(30))
    payment_installments = Column(Integer)
    payment_value = Column(Float)

    # Relationships
    order = relationship("Order", back_populates="payments")


# ===========================================================================
# ORDER REVIEWS -- customer feedback and star ratings
# ===========================================================================
class OrderReview(Base):
    __tablename__ = "order_reviews"

    review_id = Column(String(50), primary_key=True)
    order_id = Column(
        String(50),
        ForeignKey("orders.order_id"),
    )
    review_score = Column(Integer)
    review_comment_title = Column(Text, nullable=True)
    review_comment_message = Column(Text, nullable=True)
    review_creation_date = Column(DateTime, nullable=True)
    review_answer_timestamp = Column(DateTime, nullable=True)

    # Relationships
    order = relationship("Order", back_populates="reviews")
