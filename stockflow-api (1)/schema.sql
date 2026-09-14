-- Reference schema for the clothing-store version of StockFlow.
-- The app creates these automatically on startup (AUTO_CREATE_TABLES=true).

CREATE DATABASE IF NOT EXISTS stockflow CHARACTER SET utf8mb4;
USE stockflow;

CREATE TABLE categories (
  id        VARCHAR(60)  PRIMARY KEY,
  label     VARCHAR(120) NOT NULL,
  is_custom BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE products (
  id                  VARCHAR(40)  PRIMARY KEY,
  sku                 VARCHAR(40)  NOT NULL UNIQUE,
  barcode             VARCHAR(40),
  name                VARCHAR(200) NOT NULL,
  category            VARCHAR(60)  NOT NULL,
  category_label      VARCHAR(120) NOT NULL,
  price               DECIMAL(10,2) NOT NULL,
  cost                DECIMAL(10,2) NOT NULL,
  stock               INT NOT NULL DEFAULT 0,
  low_stock_threshold INT NOT NULL DEFAULT 5,
  sold_count          INT NOT NULL DEFAULT 0,
  image_url           VARCHAR(500),
  image_alt           VARCHAR(300),
  description         TEXT,
  fabric              VARCHAR(150),
  supplier            VARCHAR(200),
  colors_csv          TEXT,
  sizes_csv           TEXT,
  created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_products_barcode (barcode)
);

CREATE TABLE product_variants (
  id                    VARCHAR(40) PRIMARY KEY,
  product_id            VARCHAR(40) NOT NULL REFERENCES products(id),
  color                 VARCHAR(80) NOT NULL,
  size                  VARCHAR(40) NOT NULL,
  stock                 INT NOT NULL DEFAULT 0,
  sku                   VARCHAR(60),
  barcode               VARCHAR(60),
  last_restocked_at     DATETIME,
  last_restocked_amount INT
);

CREATE TABLE restock_log (
  id          VARCHAR(40) PRIMARY KEY,
  product_id  VARCHAR(40) NOT NULL REFERENCES products(id),
  color       VARCHAR(80) NOT NULL,
  size        VARCHAR(40) NOT NULL,
  amount      INT NOT NULL,
  timestamp   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  cost_impact DECIMAL(10,2)
);

CREATE TABLE sale_transactions (
  id             VARCHAR(40) PRIMARY KEY,
  timestamp      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  total_amount   DECIMAL(10,2) NOT NULL,
  total_cost     DECIMAL(10,2) NOT NULL DEFAULT 0,
  total_profit   DECIMAL(10,2) NOT NULL DEFAULT 0,
  payment_method ENUM('card','cash','contactless') NOT NULL,
  INDEX idx_sales_timestamp (timestamp)
);

CREATE TABLE sale_transaction_items (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  transaction_id VARCHAR(40) NOT NULL REFERENCES sale_transactions(id),
  product_id     VARCHAR(40) NOT NULL REFERENCES products(id),
  variant_id     VARCHAR(40) REFERENCES product_variants(id),
  product_name   VARCHAR(200) NOT NULL,
  sku            VARCHAR(60) NOT NULL,
  color          VARCHAR(80),
  size           VARCHAR(40),
  quantity       INT NOT NULL,
  unit_price     DECIMAL(10,2) NOT NULL,
  unit_cost      DECIMAL(10,2) NOT NULL DEFAULT 0,
  subtotal       DECIMAL(10,2) NOT NULL,
  profit         DECIMAL(10,2) NOT NULL DEFAULT 0
);

CREATE TABLE purchase_orders (
  id             VARCHAR(40) PRIMARY KEY,
  po_number      VARCHAR(40) NOT NULL UNIQUE,
  supplier_name  VARCHAR(200) NOT NULL,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expected_date  DATE,
  status         ENUM('ordered','shipped','received') NOT NULL DEFAULT 'ordered',
  total_cost     DECIMAL(10,2) NOT NULL DEFAULT 0
);

CREATE TABLE purchase_order_items (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  po_id        VARCHAR(40) NOT NULL REFERENCES purchase_orders(id),
  product_id   VARCHAR(40) NOT NULL REFERENCES products(id),
  product_name VARCHAR(200) NOT NULL,
  sku          VARCHAR(60) NOT NULL,
  color        VARCHAR(80),
  size         VARCHAR(40),
  quantity     INT NOT NULL,
  unit_cost    DECIMAL(10,2) NOT NULL
);

CREATE TABLE notifications (
  id         VARCHAR(40) PRIMARY KEY,
  title      VARCHAR(300) NOT NULL,
  message    VARCHAR(500) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  type       ENUM('alert','success','info') NOT NULL,
  `read`     BOOLEAN NOT NULL DEFAULT FALSE
);
