USE incremental_etl_db;


-- 1. Target table
CREATE TABLE IF NOT EXISTS retail_transactions (
    record_hash CHAR(64) PRIMARY KEY,

    InvoiceNo VARCHAR(20),
    StockCode VARCHAR(20),
    Description TEXT,
    Quantity INT,
    InvoiceDate DATETIME,
    UnitPrice DECIMAL(10, 2),
    CustomerID DECIMAL(10, 2),
    Country VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);


-- 2. ETL watermark table
CREATE TABLE IF NOT EXISTS etl_watermark (
    pipeline_name VARCHAR(100) PRIMARY KEY,
    last_processed_date DATETIME,
    last_run_status VARCHAR(30),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);


-- 3. ETL audit log table
CREATE TABLE IF NOT EXISTS etl_audit_log (
    audit_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    pipeline_name VARCHAR(100),
    start_time DATETIME,
    end_time DATETIME,
    records_extracted INT DEFAULT 0,
    records_inserted INT DEFAULT 0,
    records_updated INT DEFAULT 0,
    records_failed INT DEFAULT 0,
    execution_status VARCHAR(30),
    error_message TEXT
);