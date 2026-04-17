-- BrandShift Azure SQL schema (matches columns produced by azure_insert.py / UploadData)
-- All column names mirror the cleaned CSV headers so PyMSSQL queries line up 1:1.

IF OBJECT_ID('dbo.Transactions','U') IS NOT NULL DROP TABLE dbo.Transactions;
IF OBJECT_ID('dbo.Products','U')     IS NOT NULL DROP TABLE dbo.Products;
IF OBJECT_ID('dbo.Households','U')   IS NOT NULL DROP TABLE dbo.Households;

CREATE TABLE dbo.Households (
    HSHD_NUM          INT          NOT NULL PRIMARY KEY,
    L                 VARCHAR(4)   NULL,     -- Loyalty flag (Y/N)
    AGE_RANGE         VARCHAR(50)  NULL,
    MARITAL           VARCHAR(30)  NULL,
    INCOME_RANGE      VARCHAR(50)  NULL,
    HOMEOWNER         VARCHAR(30)  NULL,
    HSHD_COMPOSITION  VARCHAR(50)  NULL,
    HH_SIZE           VARCHAR(10)  NULL,
    CHILDREN          VARCHAR(10)  NULL
);

CREATE TABLE dbo.Products (
    PRODUCT_NUM           VARCHAR(20)  NOT NULL PRIMARY KEY,
    DEPARTMENT            VARCHAR(80)  NULL,
    COMMODITY             VARCHAR(80)  NULL,
    BRAND_TY              VARCHAR(20)  NULL,   -- NATIONAL / PRIVATE
    NATURAL_ORGANIC_FLAG  VARCHAR(4)   NULL    -- Y / N
);

CREATE TABLE dbo.Transactions (
    BASKET_NUM      VARCHAR(20)   NOT NULL,
    HSHD_NUM        INT           NOT NULL,
    PURCHASE_DATE   DATE          NULL,
    PRODUCT_NUM     VARCHAR(20)   NOT NULL,
    SPEND           DECIMAL(10,2) NULL,
    UNITS           INT           NULL,
    STORE_R         VARCHAR(20)   NULL,       -- CENTRAL / EAST / WEST / SOUTH
    WEEK_NUM        INT           NULL,
    [YEAR]          INT           NULL,
    CONSTRAINT FK_Transactions_Households FOREIGN KEY (HSHD_NUM)    REFERENCES dbo.Households(HSHD_NUM),
    CONSTRAINT FK_Transactions_Products   FOREIGN KEY (PRODUCT_NUM) REFERENCES dbo.Products(PRODUCT_NUM)
);

-- Indexes that back the hottest query paths (search by HH, analytics, upload replace)
CREATE INDEX IX_Transactions_Hshd_num     ON dbo.Transactions(HSHD_NUM);
CREATE INDEX IX_Transactions_Product_num  ON dbo.Transactions(PRODUCT_NUM);
CREATE INDEX IX_Transactions_YearWeek     ON dbo.Transactions([YEAR], WEEK_NUM);
CREATE INDEX IX_Transactions_PurchaseDate ON dbo.Transactions(PURCHASE_DATE);

-- Users table is created lazily by the Register/Login Azure Functions
-- using shared_code.auth.ensure_users_table(), but the shape is:
-- CREATE TABLE dbo.Users (
--     user_id       INT IDENTITY(1,1) PRIMARY KEY,
--     username      VARCHAR(40)  NOT NULL UNIQUE,
--     email         VARCHAR(120) NOT NULL UNIQUE,
--     password_hash VARCHAR(256) NOT NULL,  -- pbkdf2_sha256$iterations$salt$hash
--     created_at    DATETIME2    NOT NULL DEFAULT SYSUTCDATETIME()
-- );
