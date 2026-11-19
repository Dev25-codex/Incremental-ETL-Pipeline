# Incremental ETL Pipeline
## Use Case 02 – Data Warehousing with Star Schema and SCD Type 2

### 1. Project Overview

This project implements an Incremental ETL Pipeline using Python, Pandas, and MySQL.

The main objective is to extract retail transaction data, transform it into a structured format, load dimension and fact tables, and maintain historical product information using Slowly Changing Dimension Type 2 (SCD Type 2).

**Dataset:** Online Retail.xlsx  
**Source Records:** 541,909  
**Source Columns:** 8

### 2. Technologies Used

- Python
- Pandas
- NumPy
- MySQL
- SQLAlchemy
- MySQL Connector
- Jupyter Notebook
- Visual Studio Code

### 3. Project Architecture

The pipeline follows this workflow:

```text
        Online Retail.xlsx
                |
                v
             Extract
                |
                v
            Transform
                |
                v
        Load Dimensions
                |
                v
          SCD Type 2
                |
                v
           Load Facts
                |
                v
          MySQL Database
                |
                v
         Data Validation
```

### 4. Star Schema Design

The data warehouse contains five tables.

**Dimension Tables:**

1. dim_product
2. dim_customer
3. dim_date
4. dim_region

**Fact Table:**

5. fact_sales

The fact table stores transaction-level information and connects to the dimension tables through foreign keys.

### 5. ETL Process

**Step 1 – Extract**

- Read the Online Retail Excel dataset using Pandas.
- Extract 541,909 transaction records.

**Step 2 – Transform**

- Clean and prepare source data.
- Process product and customer information.
- Generate date and region dimensions.
- Prepare dimension datasets for loading.

**Step 3 – Load Dimensions**

- Load product dimension.
- Load customer dimension.
- Load date dimension.
- Load region dimension.
- Avoid duplicate dimension records.

**Step 4 – SCD Type 2 Implementation**

Implemented Slowly Changing Dimension Type 2 to maintain historical product information.

When a product description changes:

- Close the previous record.
- Set its is_current value to 0.
- Insert a new version.
- Set its is_current value to 1.
- Maintain effective_from and effective_to dates.

**Example:**

| Product Code | Product Name | Effective From | Effective To | Current |
|---|---|---|---|---|
| 21818 | GLITTER CHRISTMAS HEART | 2010-12-01 | 2011-02-02 | 0 |
| 21818 | GLITTER HEART DECORATION | 2011-02-02 | NULL | 1 |

**Step 5 – Load Fact Table**

- Map transactions to the correct product version.
- Map customer, date, and region keys.
- Calculate sales amount using Quantity × UnitPrice.
- Load records in batches of 5,000.
- Validate the final record count.

### 6. Final Database Record Counts

| Table Name | Records |
|---|---:|
| dim_product | 4,071 |
| dim_customer | 4,373 |
| dim_date | 305 |
| dim_region | 38 |
| fact_sales | 541,909 |

### 7. Data Quality Validation

The following checks were performed:

- NULL product code validation.
- Duplicate current product validation.
- Invalid effective date validation.
- Multiple or missing current product version validation.
- Foreign key validation.
- NULL sales amount validation.
- Fact and dimension relationship validation.
- Negative sales record analysis.

**Validation Results:**

| Validation | Result |
|---|---:|
| NULL Product Codes | 0 |
| Duplicate Current Product Codes | 0 |
| Invalid Effective Dates | 0 |
| Invalid Current Versions | 0 |
| Missing Foreign Key References | 0 |
| NULL Sales Amount | 0 |
| Negative Sales Records | 9,290 |

Negative sales records are retained because they can represent product returns or credit transactions.

### 8. SCD Type 2 Validation

Product code 21818 was used to validate historical version management.

| Product Version | Product Key | Fact Records |
|---|---:|---:|
| Old Version | 855 | 25 |
| New Version | 4071 | 156 |
| Total | | 181 |

The validation confirmed that transactions were mapped to the appropriate historical product version.

### 9. Project Execution

Run the pipeline from the project root directory:

```bash
python src/use_case_02/pipeline.py
```

Make sure the `.env` file contains the correct MySQL connection settings.

**Note:** Do not upload `.env` or database passwords to GitHub.

### 10. Key Learning Outcomes

- ETL Pipeline Development
- Data Cleaning and Transformation
- Star Schema Data Modeling
- Fact and Dimension Table Design
- Slowly Changing Dimension Type 2
- Historical Data Management
- Batch Data Loading
- SQL Data Validation
- Referential Integrity

### 11. Conclusion

Successfully implemented and validated a retail data warehouse pipeline using Python and MySQL.

The project demonstrates ETL development, dimensional modeling, historical data tracking through SCD Type 2, and data quality validation.