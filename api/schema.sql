-- Azure SQL Database Setup Script for BrandShift

-- 1. Create Households Table
CREATE TABLE dbo.Households (
    Hshd_num INT PRIMARY KEY,
    Lytl_status VARCHAR(50),
    Income_Range VARCHAR(50),
    Marital_Status VARCHAR(50),
    Hshd_Composition VARCHAR(50),
    Home_Desc VARCHAR(50),
    Household_Size VARCHAR(50),
    Kids_Count VARCHAR(50)
);

-- 2. Create Products Table
CREATE TABLE dbo.Products (
    Product_num VARCHAR(50) PRIMARY KEY,
    Department VARCHAR(100),
    Commodity VARCHAR(100),
    Brand_Type VARCHAR(50), -- e.g., 'National' or 'Private'
    Natural_Organic_Flag BIT -- 1 for True, 0 for False
);

-- 3. Create Transactions Table
-- Note: Does not have a single column primary key since it's transactional log data.
CREATE TABLE dbo.Transactions (
    Hshd_num INT,
    Basket_num VARCHAR(50),
    [Date] DATE,
    Product_num VARCHAR(50),
    Spend DECIMAL(10, 2),
    Units INT,
    Store_Region VARCHAR(50),
    Week_Num INT,
    Year_Num INT,
    FOREIGN KEY (Hshd_num) REFERENCES dbo.Households(Hshd_num),
    FOREIGN KEY (Product_num) REFERENCES dbo.Products(Product_num)
);

-- Create Index for faster searching specifically for Hshd_num
CREATE INDEX IX_Transactions_Hshd_num ON dbo.Transactions(Hshd_num);
