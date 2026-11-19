USE incremental_etl_db_test;

-- 1. Product Dimension (SCD Type 2)
CREATE TABLE IF NOT EXISTS dim_product (
    product_key INT AUTO_INCREMENT PRIMARY KEY,
    product_code VARCHAR(50) NOT NULL,
    product_name VARCHAR(255),
    effective_from DATE,
    effective_to DATE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE
);

-- 2. Customer Dimension
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_key INT AUTO_INCREMENT PRIMARY KEY,
    customer_id BIGINT UNIQUE,
    effective_from DATETIME,
    effective_to DATETIME,
    is_current BOOLEAN DEFAULT TRUE
);

-- 3. Date Dimension
CREATE TABLE IF NOT EXISTS dim_date (
    date_key INT PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    day INT,
    month INT,
    quarter INT,
    year INT
);

-- 4. Region Dimension
CREATE TABLE IF NOT EXISTS dim_region (
    region_key INT AUTO_INCREMENT PRIMARY KEY,
    country VARCHAR(100) NOT NULL UNIQUE
);

-- 5. Sales Fact Table
CREATE TABLE IF NOT EXISTS fact_sales (
    sales_key BIGINT AUTO_INCREMENT PRIMARY KEY,

    invoice_no VARCHAR(50),

    product_key INT NOT NULL,
    customer_key INT NOT NULL,
    date_key INT NOT NULL,
    region_key INT NOT NULL,

    quantity INT,
    unit_price DECIMAL(12,2),
    sales_amount DECIMAL(14,2),

    FOREIGN KEY (product_key)
        REFERENCES dim_product(product_key),

    FOREIGN KEY (customer_key)
        REFERENCES dim_customer(customer_key),

    FOREIGN KEY (date_key)
        REFERENCES dim_date(date_key),

    FOREIGN KEY (region_key)
        REFERENCES dim_region(region_key)
);