using GH_Mall_Linking.Data;
using GH_Mall_Linking.Models;
using Microsoft.EntityFrameworkCore;
using System;
using System.Linq;

namespace GH_Mall_Linking.Services
{
    public static class DatabaseInitializer
    {
        public static void Initialize()
        {
            using (var context = new AppDbContext())
            {
                SQLitePCL.Batteries.Init();

                // Ensure SQLite Database and EF Core schema are created
                context.Database.EnsureCreated();

                // 1. Ensure EF-only auxiliary tables exist
                EnsureEfOnlyTablesExist(context);

                // 2. Ensure Staging tables exist for Native C# & Python Sync
                EnsureStagingTablesExist(context);

                // 3. Clean up legacy Paradox tables if they still exist
                DropLegacyTables(context);

                // Seed Default System Configuration
                if (!context.Configurations.Any())
                {
                    context.Configurations.AddRange(
                        new Configuration { Key = "ParadoxDBFolder", Value = @"C:\", Description = "Paradox DB directory" },
                        new Configuration { Key = "AccLocalFolder", Value = @"C:\GH_ACC_EXPORT", Description = "Local export folder" },
                        new Configuration { Key = "AccSharedFolder", Value = @"", Description = "Optional shared network destination" },
                        new Configuration { Key = "PythonPath", Value = @"python", Description = "Python Executable or venv path" },

                        new Configuration { Key = "StoreCode", Value = "FG01", Description = "Store Identifier Code" },
                        new Configuration { Key = "MallName", Value = "GREENHILLS", Description = "Mall Name" },
                        new Configuration { Key = "TerminalNo", Value = "01", Description = "Terminal / POS ID" },
                        new Configuration { Key = "PosCode", Value = "POS01", Description = "POS Identifier Code" },
                        new Configuration { Key = "Department", Value = "MIS", Description = "Department Name" },

                        new Configuration { Key = "GrandTotal", Value = "0.00", Description = "Beginning Grand Total" },
                        new Configuration { Key = "ZCount", Value = "1", Description = "Active Z-Count" },
                        new Configuration { Key = "BatchLimit", Value = "100", Description = "Batch Processing Limit" },

                        new Configuration { Key = "Password", Value = "Admin", Description = "Login Password" }
                    );
                    context.SaveChanges();
                }

                // Seed Default GH Mall Payment Methods & Mappings
                if (!context.PaymentMethods.Any())
                {
                    var cash = new PaymentMethod { MethodName = "Cash", GhCode = "01", IsDefault = true, IsActive = true };
                    var card = new PaymentMethod { MethodName = "Credit / Debit Card", GhCode = "02", IsActive = true };
                    var gcash = new PaymentMethod { MethodName = "GCash", GhCode = "03", IsActive = true };
                    var maya = new PaymentMethod { MethodName = "Maya", GhCode = "03", IsActive = true };
                    var panda = new PaymentMethod { MethodName = "FoodPanda", GhCode = "04", IsActive = true };
                    var grab = new PaymentMethod { MethodName = "GrabFood", GhCode = "04", IsActive = true };

                    context.PaymentMethods.AddRange(cash, card, gcash, maya, panda, grab);
                    context.SaveChanges();

                    context.PaymentMethodKeywords.AddRange(
                        new PaymentMethodKeyword { PaymentMethodId = cash.Id, Keyword = "CASH" },
                        new PaymentMethodKeyword { PaymentMethodId = card.Id, Keyword = "VISA" },
                        new PaymentMethodKeyword { PaymentMethodId = card.Id, Keyword = "MASTER" },
                        new PaymentMethodKeyword { PaymentMethodId = gcash.Id, Keyword = "GCASH" },
                        new PaymentMethodKeyword { PaymentMethodId = maya.Id, Keyword = "MAYA" },
                        new PaymentMethodKeyword { PaymentMethodId = panda.Id, Keyword = "PANDA" },
                        new PaymentMethodKeyword { PaymentMethodId = grab.Id, Keyword = "GRAB" }
                    );
                    context.SaveChanges();
                }
                
            }
        }

        private static void EnsureStagingTablesExist(AppDbContext context)
        {
            // FIX: StagingOrders' primary key was OrderNo alone. Paradox and Cloud
            // export the SAME order numbers for the same physical transactions, so
            // whichever source synced second collided on that key -- ON CONFLICT
            // overwrote Time/Total/Void/etc with the new source's values but never
            // updated the Source column itself, silently making Cloud's data
            // invisible to any query filtering by Source='CLOUD'. Composite key
            // (OrderNo, Source) lets both sources' rows for the same order coexist.
            //
            // Also: GrandTotalTrackers is now created explicitly here via raw SQL
            // instead of relying only on EF's EnsureCreated(), which is a no-op once
            // the .db file already exists (a recurring source of "table doesn't
            // exist" bugs earlier in this project).
            context.Database.ExecuteSqlRaw(@"
                CREATE TABLE IF NOT EXISTS StagingOrders (
                    OrderNo TEXT NOT NULL,
                    Source TEXT NOT NULL,
                    Time TEXT,
                    AcDate TEXT,
                    NoGuest INTEGER DEFAULT 0,
                    Price REAL DEFAULT 0.0,
                    Gst REAL DEFAULT 0.0,
                    Pst REAL DEFAULT 0.0,
                    Disc_amt REAL DEFAULT 0.0,
                    Disc_per REAL DEFAULT 0.0,
                    Serv REAL DEFAULT 0.0,
                    Total REAL DEFAULT 0.0,
                    DiscType TEXT,
                    Void TEXT DEFAULT '0',
                    Printed TEXT,
                    Posted TEXT,
                    String1 TEXT,
                    OrderNo2 TEXT,
                    SyncedAt TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (OrderNo, Source)
                );

                CREATE TABLE IF NOT EXISTS StagingItems (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    OrderNo TEXT NOT NULL,
                    Source TEXT NOT NULL,
                    MenuKey TEXT,
                    Status TEXT,
                    MenuNo TEXT,
                    ItemNo TEXT,
                    Description TEXT,
                    Qty REAL DEFAULT 1.0,
                    Size TEXT,
                    PriceBefDisc REAL DEFAULT 0.0,
                    DiscValue REAL DEFAULT 0.0,
                    Discount REAL DEFAULT 0.0,
                    DiscCode TEXT,
                    DiscName TEXT
                );

                CREATE TABLE IF NOT EXISTS StagingPayments (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    OrderNo TEXT NOT NULL,
                    Source TEXT NOT NULL,
                    SeqNo INTEGER DEFAULT 0,
                    PayID TEXT,
                    PayName TEXT,
                    Amount REAL DEFAULT 0.0,
                    OrgAmount REAL DEFAULT 0.0,
                    ExRate REAL DEFAULT 1.0,
                    PayDT TEXT,
                    Change REAL DEFAULT 0.0,
                    PayName2 TEXT
                );

                CREATE TABLE IF NOT EXISTS GrandTotalTrackers (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    TargetDate TEXT UNIQUE,
                    OldGrandTotal TEXT DEFAULT '0.00',
                    NewGrandTotal TEXT DEFAULT '0.00',
                    DayGrossSales TEXT DEFAULT '0.00',
                    PreviousZCount INTEGER DEFAULT 0,
                    NewZCount INTEGER DEFAULT 0,
                    CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
                );
            ");
        }

        private static void DropLegacyTables(AppDbContext context)
        {
            // Also drops the earlier per-source table set (ParadoxOrdersBkup/
            // CloudOrders/etc) now that Staging* has fully replaced them.
            context.Database.ExecuteSqlRaw(@"
                DROP TABLE IF EXISTS ParadoxOrders;
                DROP TABLE IF EXISTS ParadoxItems;
                DROP TABLE IF EXISTS ParadoxOrdersBkup;
                DROP TABLE IF EXISTS ParadoxItemsBkup;
                DROP TABLE IF EXISTS ParadoxPaymentsBkup;
                DROP TABLE IF EXISTS CloudOrders;
                DROP TABLE IF EXISTS CloudItems;
                DROP TABLE IF EXISTS CloudPayments;
            ");
        }

        private static void EnsureEfOnlyTablesExist(AppDbContext context)
        {
            context.Database.ExecuteSqlRaw(@"
                CREATE TABLE IF NOT EXISTS Logs (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Timestamp TEXT NOT NULL,
                    Level TEXT NOT NULL,
                    Message TEXT NOT NULL,
                    Source TEXT
                );

                CREATE TABLE IF NOT EXISTS SalesLines (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    EodRunId TEXT,
                    LineCode TEXT,
                    SalesTime TEXT,
                    PosCode TEXT,
                    SalesDate TEXT,
                    TerminalNo INTEGER,
                    GrossSales REAL,
                    VatableSales REAL,
                    VatAmount REAL,
                    NetSales REAL,
                    FormattedFixedString TEXT
                );

                CREATE TABLE IF NOT EXISTS EodTransactions (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    StoreCode TEXT,
                    MallName TEXT,
                    TransactionDate TEXT UNIQUE,
                    GrossSales REAL,
                    NetSales REAL,
                    TotalDiscount REAL,
                    TotalVat REAL,
                    TransactionCount INTEGER,
                    Status TEXT,
                    CreatedAt TEXT
                );

                CREATE TABLE IF NOT EXISTS PaymentMethods (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    MethodName TEXT,
                    GhCode TEXT,
                    IsDefault INTEGER,
                    IsActive INTEGER,
                    CreatedAt TEXT
                );

                CREATE TABLE IF NOT EXISTS PaymentMethodKeywords (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    PaymentMethodId INTEGER,
                    Keyword TEXT
                );

                CREATE TABLE IF NOT EXISTS PaymentMappings (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    LocalPaymentCode TEXT,
                    MallPaymentCode TEXT,
                    PaymentDescription TEXT,
                    IsActive INTEGER
                );
            ");
        }
    }
}